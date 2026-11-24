"""Schedule OKLine read receipts independently of serial text replies."""
from __future__ import annotations

import json
import logging
from queue import Empty, Queue
import random
import threading
import time

from .ai import AiError, AiTimeoutError, AiRateLimitError, validate_visual_descriptions
from .diagnostics import log_event
from .okline_errors import SendNotStarted, LineHistoryError
from .group_replies import mentions_self


class MonitorController:
    def __init__(self, repository, line, ai, sleeper=time.sleep, region_blocked=False,
                 on_exchange_committed=None, logger=None):
        self.repository=repository; self.line=line; self.ai=ai
        self.store=line.store; self.sleeper=sleeper; self.region_blocked=region_blocked
        self.on_exchange_committed=on_exchange_committed
        self.logger=logger or logging.getLogger('sweety.monitor')
        self._lock=threading.RLock(); self._cycle_lock=threading.Lock()
        self._stop_event=threading.Event(); self._thread=None
        self._reader = None
        self._enabled=False; self._status='stopped'; self._message=''
        self._current_target=None; self._ai_timeout_alert=False
        line.allow_receiving=lambda:self._enabled and not self._stop_event.is_set()

    def start(self, background=True):
        with self._lock:
            if self._enabled or any(thread and thread.is_alive() for thread in (self._thread, self._reader)):
                return False
            settings = self.repository.get_settings()
            if settings.get('ai_provider') == 'codex':
                status = self.ai.codex.status(refresh=True)
                if not status.get('ready'):
                    self._set_status('codex_not_ready', status.get('status', 'codex_unavailable')); return False
            else:
                key_field = 'openai_api_key' if settings.get('ai_provider') == 'openai' else 'agnes_api_key'
                if not str(settings.get(key_field, '')).strip():
                    self._set_status('api_key_required'); return False
            if self.region_blocked:
                self._set_status('region_blocked'); return False
            if not self.line.connected():
                self._set_status('line_login_required'); return False
            if not self.store.targets():
                self._set_status('target_required'); return False
            self.store.recover()
            self._stop_event=threading.Event()
            self.line.prepare_receiving(time.time())
            self._enabled=True; self._ai_timeout_alert=False
            self._set_status('monitoring')
            try:
                self.line.start_receiving()
                if background:
                    ready = Queue()
                    self._reader = threading.Thread(target=self._run_read_loop, args=(self._stop_event, ready),
                                                    daemon=True, name='SweetyReadScheduler')
                    self._thread=threading.Thread(target=self._run_loop,args=(self._stop_event, ready),daemon=True,name='SweetyTextMonitor')
                    self._reader.start()
                    self._thread.start()
            except Exception as exc:
                self._enabled=False; self._stop_event.set(); self.line.stop_receiving()
                self._set_status('error',str(exc)); return False
        return True

    def stop(self):
        # Set the captured generation's token immediately, even while AI/network is busy.
        was_enabled=self._enabled
        self._stop_event.set(); self._enabled=False
        if hasattr(self.ai, 'cancel'):
            self.ai.cancel()
        self.line.stop_receiving(); self.store.archive_pending()
        self._set_status('stopped'); self._ai_timeout_alert=False
        return was_enabled

    def snapshot(self):
        return dict(enabled=self._enabled,testMode=False,status=self._status,message=self._message,
                    currentTarget=self._current_target,aiTimeoutAlert=self._ai_timeout_alert,
                    selectedTargetCount=len(self.store.targets()))

    def _set_status(self, status, message='', target=None):
        self._status=status; self._message=message; self._current_target=target

    def _valid(self, stop, scope, target_id):
        return (self._enabled and not stop.is_set() and self.line.connected()
                and self.store.scope==scope and any(t['id']==target_id for t in self.store.targets()))

    def _wait_until(self, stop, deadline):
        remaining = deadline - time.monotonic()
        if remaining > 0:
            if self.sleeper is time.sleep:
                stop.wait(remaining)
            else:
                self.sleeper(remaining)

    def run_cycle(self, stop_event=None):
        stop=stop_event or self._stop_event
        if not self._enabled or stop.is_set() or (self._reader and self._reader.is_alive()):
            return False
        if not self._cycle_lock.acquire(blocking=False):
            return False
        try:
            return self._cycle(stop)
        finally:
            self._cycle_lock.release()

    def _pending_receipts(self):
        active = {target['id'] for target in self.store.targets()}
        first_by_target = {}
        for row in self.store.rows():
            target_id = row['target_id']
            if target_id in active:
                received = row['received_at']
                first_by_target[target_id] = min(first_by_target.get(target_id, received), received)
        return first_by_target

    def _prepare_batch(self, stop, scope, target_id):
        with self.line.lock:
            if not self._valid(stop, scope, target_id):
                return None
            target = self.repository.get_target(target_id)
            queued = self.store.rows(target_id=target_id)
            # LINE message IDs break timestamp ties for both batching and the read watermark.
            queued.sort(key=lambda row: (row['created'], len(row['id']), row['id']))
            rows = queued[:8]
            if not rows or stop.is_set():
                return None
            for row in rows:
                self.store.update(row['id'], 'processing')
            if stop.is_set():
                self._archive_batch(scope, rows)
                return None
            try:
                self.line.mark_as_read(target['line_mid'], rows[-1]['id'])
            except Exception as exc:
                log_event(self.logger, 'line_mark_read_failed', target_id=target_id, error=type(exc).__name__)
            return scope, target_id, rows, {row['id'] for row in queued}, time.monotonic()

    def _cycle(self, stop):
        scope = self.store.scope
        processed = False
        for target_id, received in self._pending_receipts().items():
            self._wait_until(stop, received + random.uniform(3, 10))
            batch = self._prepare_batch(stop, scope, target_id)
            if batch is not None:
                processed = self._reply_batch(stop, *batch) or processed
        if not stop.is_set() and self._status not in ('error', 'ai_rate_limited'):
            self._set_status('monitoring' if processed else 'waiting')
        return processed

    def _reply_batch(self, stop, scope, target_id, rows, exclude_ids, typing_started):
        if not self._valid(stop, scope, target_id):
            self._archive_batch(scope, rows)
            return False
        target = self.repository.get_target(target_id)
        self._set_status('processing',target=target['name'])
        inputs=[]
        sending=False
        try:
            settings = self.repository.get_settings()
            typing_deadline = typing_started + random.uniform(
                settings['reply_delay_min_seconds'], settings['reply_delay_max_seconds'])
            history=self.line.history_for_reply(target_id,
                int(settings.get('history_limit',6)),
                exclude_ids=exclude_ids,
                before=min(row['created'] for row in rows),
                allowed=lambda:self._valid(stop,scope,target_id))
            for row in rows:
                raw=json.loads(row['raw'])
                kind=int(raw.get('contentType') or 0)
                item={'id':row['id'],'text':str(raw.get('text') or ''),
                      'createdTime':raw.get('createdTime'),
                      'senderId':raw.get('from'), 'chatId':raw.get('to'),
                      'isGroup':int(raw.get('toType') or 0)!=0,
                      'mentionedSelf':mentions_self(raw,self.store.account),
                      'relatedMessageId':raw.get('relatedMessageId'), 'contentType':kind}
                if kind in (1,7):
                    item['images']=self.line.image_inputs(raw,allowed=lambda:self._valid(stop,scope,target_id))
                    if kind==7:
                        item['stickerText']=str((raw.get('contentMetadata') or {}).get('STKTXT') or '')[:1000]
                if not self._valid(stop,scope,target_id):
                    raise RuntimeError('reply_cancelled')
                inputs.append(item)
            self._ai_timeout_alert=False
            decision=self.ai.generate_reply(target=target,incoming_messages=inputs,history=history,
                total_messages=target["round_trips"]*2+len(inputs),settings=self.repository.get_settings())
            validate_visual_descriptions(decision,inputs)
            if not self._valid(stop,scope,target_id):
                return False
            self._wait_until(stop, typing_deadline)
            if not self._valid(stop,scope,target_id):
                return False
            # The receipt and its ledger commit share the SDK lock with incoming echoes.
            with self.line.lock:
                if not self._valid(stop,scope,target_id):
                    return False
                for row in rows:self.store.update(row['id'],'sending')
                sending=True
                receipt=self.line.send(target_id,decision.msg_reply,
                    allowed=lambda:self._valid(stop,scope,target_id),expected_scope=scope)
                self.store.complete(rows,receipt)
            log_event(self.logger,'exchange_committed',target_id=target_id,receipt=receipt)
            if self.on_exchange_committed:
                try:self.on_exchange_committed()
                except Exception as exc:log_event(self.logger,'metrics_callback_failed',error=type(exc).__name__)
            return True
        except Exception as exc:
            if not sending and not self._valid(stop, scope, target_id):
                return False
            state='uncertain' if sending and not isinstance(exc,SendNotStarted) else 'failed'
            for row in rows:self.store.update(row['id'],state,error=type(exc).__name__)
            if isinstance(exc,AiTimeoutError):self._ai_timeout_alert=True
            if not stop.is_set():
                if isinstance(exc,AiRateLimitError):self._set_status('ai_rate_limited',target=target['name'])
                else:self._set_status('error',('LINE 交談歷史讀取失敗，本次未回覆。' if isinstance(exc,LineHistoryError) else 'line_send_uncertain' if state=='uncertain' else str(exc) if isinstance(exc,AiError) and str(exc).startswith('codex_') else type(exc).__name__),target['name'])
            log_event(self.logger,'reply_failed',target_id=target_id,status=state,error=type(exc).__name__)
            return False
        finally:
            if not sending and not self._valid(stop, scope, target_id):
                self._archive_batch(scope, rows)

    def _archive_batch(self, scope, rows):
        with self.line.lock:
            if self.store.scope == scope:
                for row in rows:
                    self.store.update(row['id'], 'archived')

    def _run_read_loop(self, stop, ready):
        deadlines = {}
        try:
            while not stop.is_set():
                self.line.wake.clear()
                scope = self.store.scope
                received = self._pending_receipts()
                next_deadlines = {}
                for target_id, stamp in received.items():
                    previous = deadlines.get(target_id)
                    if previous is None or previous[0] != stamp:
                        previous = stamp, stamp + random.uniform(3, 10)
                    next_deadlines[target_id] = previous
                deadlines = next_deadlines
                if not deadlines:
                    self.line.wake.wait(10)
                    continue
                target_id = min(deadlines, key=lambda key: deadlines[key][1])
                remaining = deadlines[target_id][1] - time.monotonic()
                if remaining > 0:
                    self.line.wake.wait(remaining)
                    continue
                batch = self._prepare_batch(stop, scope, target_id)
                if batch is not None and not stop.is_set():
                    ready.put(batch)
                else:
                    self.line.wake.wait(0.1)
        except Exception as exc:
            if not stop.is_set():
                self._set_status('error', type(exc).__name__)
                log_event(self.logger, 'read_scheduler_failed', error=type(exc).__name__)
                stop.set()
                ready.put(None)

    def _run_loop(self, stop, ready):
        try:
            while not stop.is_set():
                if not self.line.connected():
                    self._set_status('line_login_required')
                    break
                try:
                    batch = ready.get(timeout=1)
                except Empty:
                    if self._status not in ('waiting', 'error', 'ai_rate_limited'):
                        self._set_status('waiting')
                    continue
                if batch is None or stop.is_set():
                    break
                if self._reply_batch(stop, *batch) and not stop.is_set():
                    self._set_status('monitoring')
        except Exception as exc:
            self._set_status('error', type(exc).__name__)
            log_event(self.logger, 'monitor_worker_failed', error=type(exc).__name__)
        finally:
            stop.set()
            self._enabled = False
            self.line.stop_receiving()
            self.store.archive_pending()
