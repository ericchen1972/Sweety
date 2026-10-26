"""QR authentication and background LINE transport. No desktop UI operations."""
import base64
import io
import json
import re
import threading
import time
import logging
from .diagnostics import log_event
from .okline_session import sdk_factory
from .okline_errors import SendNotStarted, login_error_details


def avatar_url(picture_path):
    """Only render public LINE profile paths; never relay arbitrary remote URLs."""
    if not isinstance(picture_path, str) or picture_path.startswith('//'): return ''
    prefix = 'https://profile.line-scdn.net/'
    path = picture_path[len(prefix):] if picture_path.startswith(prefix) else picture_path.lstrip('/')
    if not path or not re.fullmatch(r'[A-Za-z0-9_./~-]+', path) or '..' in path.split('/'):
        return ''
    return prefix + path


def normalize_contacts(response, blocked):
    if not isinstance(response, dict) or not isinstance(response.get('contacts'), dict):
        raise ValueError('line_contacts_shape_unknown')
    result=[]
    for mid,wrapper in response['contacts'].items():
        c=wrapper.get('contact',wrapper)
        contact_id=str(c.get('mid') or mid)
        original=str(c.get('displayName') or mid)
        alias=str(c.get('displayNameOverridden') or '')
        row={'id':contact_id,'name':alias or original,'alias':alias,'originalName':original,'blocked':contact_id in blocked}
        if 'picturePath' in c: row['avatarUrl']=avatar_url(c['picturePath'])
        result.append(row)
    return result


def normalize_groups(response, joined):
    if not isinstance(response,dict) or not isinstance(response.get('chats'),list):
        raise ValueError('line_groups_shape_unknown')
    result=[]
    for chat in response['chats']:
        mid=chat.get('chatMid')
        if not mid or mid not in joined: continue
        name=str(chat.get('chatName') or mid)
        members=((chat.get('extra') or {}).get('groupExtra') or {}).get('memberMids')
        if isinstance(members,(dict,list)): name += f' ({len(members)})'
        result.append({'id':mid,'name':name,'blocked':False,'kind':'group',
                       'avatarUrl':avatar_url(chat.get('picturePath'))})
    return result


def message_list(value):
    if isinstance(value,list): return [m for m in value if isinstance(m,dict) and m.get('id')]
    if isinstance(value,dict):
        for key in ('messages','result'):
            if key in value: return message_list(value[key])
    raise ValueError('line_history_shape_unknown')


class LineService:
    def __init__(self,repo,store,*,factory=None,vault=None):
        self.repo=repo;self.store=store;self.vault=vault
        self.factory=factory or (lambda:sdk_factory(self.vault))
        self.allow_receiving=lambda:False
        self.receive_cutoff=0
        self.recover_wait_reply=lambda message,**kw:False
        self.cancel_recovery=lambda:None
        self.stream_token=None
        self.api=None;self.receiver=None;self.login_api=None
        # Lifecycle and SDK operations share one reentrant lock: no lock inversion.
        self.lock=self.guard=threading.RLock()
        self.generation=0;self.wake=threading.Event();self.stop_stream=threading.Event()
        self.state={'status':'disconnected','qr':'','pin':'','error':''}
        self.owner='local';self.stream_thread=None

    def snapshot(self):
        with self.guard:
            if self.owner!='local': return {'status':'disconnected','qr':'','pin':'','error':''}
            if self.state.get('expiresAt',0) and time.time()>self.state['expiresAt'] and self.state['status'] in {'qr','pin','connecting'}:
                self.generation+=1
                self.state={'status':'expired','qr':'','pin':'','error':'line_qr_expired'}
            return dict(self.state)

    def main_window_exists(self):
        return self.connected()

    def connected(self):
        return self.snapshot()['status']=='connected' and bool(self.store.scope)

    def login(self):
        if self.connected(): return self.snapshot()
        self.disconnect(clear=False)
        with self.guard:
            generation=self.generation
            self.owner='local'
            if self.vault:
                from .okline_session import SessionVault
                self.vault=SessionVault(self.vault.directory,self.owner)
            self.state={'status':'connecting','qr':'','pin':'','error':'','expiresAt':time.time()+180}
        threading.Thread(target=self._login,args=(generation,),daemon=True,name='Sweety-QR').start()
        return self.snapshot()

    def _login(self,generation):
        api=None
        def publish(**values):
            with self.guard:
                if generation!=self.generation or self.owner!='local' or time.time()>self.state.get('expiresAt',0):
                    raise ValueError('line_login_cancelled')
                self.state.update(values)
        try:
            api=self.factory();self.login_api=api
            def qr(url):
                import qrcode
                out=io.BytesIO();qrcode.make(url).save(out,format='PNG')
                publish(status='qr',qr='data:image/png;base64,'+base64.b64encode(out.getvalue()).decode())
            api.qr_login(on_qr=qr,on_pin=lambda pin:publish(status='pin',pin=str(pin)),wait_seconds=180)
            publish(status='connecting',qr='',pin='')
            self._accept(api,generation)
        except Exception as exc:
            with self.guard:
                if generation==self.generation:
                    self.api=None;self.store.activate('')
                    self.state={'status':'error','qr':'','pin':'','error':'line_login_failed: '+login_error_details(exc)}
            if api is not None: api.close()
        finally:
            if self.login_api is api: self.login_api=None

    def _accept(self,api,generation):
        profile=api.get_profile()
        account=profile.get('mid') or api.tokens.mid
        if not account: raise ValueError('line_profile_missing')
        with self.guard:
            if generation!=self.generation or self.owner!='local': raise ValueError('line_login_cancelled')
            self.api=api;self.store.activate(account)
            self.refresh_contacts()
            if self.store.cursor() is None: self.store.advance(api.get_last_op_revision())
            api.save_tokens()
            self.state={'status':'connected','name':str(profile.get('displayName') or ''),'avatarUrl':avatar_url(profile.get('picturePath')),'qr':'','pin':'','error':''}
            self.store.recover()
            self.archive_pending()


    def restore(self):
        if not self.vault: return
        if self.owner!='local':
            self.disconnect(clear=False)
            self.owner='local'
            from .okline_session import SessionVault
            self.vault=SessionVault(self.vault.directory,self.owner)
        generation=self.generation
        def run():
            api=None
            try:
                saved=self.vault.load()
                if not saved: return
                api=sdk_factory(self.vault,saved)
                self._accept(api,generation)
            except Exception as exc:
                if api: api.close()
                with self.guard:
                    if generation==self.generation:
                        self.state={'status':'error','error':'line_restore_failed: '+login_error_details(exc),'qr':'','pin':''}
        threading.Thread(target=run,daemon=True,name='Sweety-LineRestore').start()

    def disconnect(self,clear=True):
        with self.guard:
            self.generation+=1
            self.stop_stream.set();self.wake.set()
            self.state={'status':'disconnected','qr':'','pin':'','error':''}
            self.store.activate('')
            clients=(self.receiver,self.login_api,self.api)
            self.api=None;self.receiver=None;self.login_api=None
        if clear and clients[2] is not None:
            try:
                with self.lock: clients[2].auth.logout()
            except Exception:
                self.state['error']='已清除本機登入；遠端登出未確認，可在手機 LINE 的登入裝置檢查。'
        for client in clients:
            if client is not None:
                try:
                    if hasattr(client,'ops'): client.ops.request_reconnect()
                    client.close()
                except Exception: pass
        if clear and self.vault: self.vault.clear()

    def refresh_contacts(self):
        with self.lock:
            if self.api is None: raise ValueError('line_login_required')
            ids=self.api.get_all_contact_ids()
            blocked=self.api.get_blocked_contact_ids()
            if not isinstance(ids,list) or not isinstance(blocked,list): raise ValueError('line_contacts_shape_unknown')
            response=self.api.get_contacts(list(dict.fromkeys(ids+blocked)))
            contacts=normalize_contacts(response,set(blocked))
            groups=self.api.get_all_chat_mids(with_member_chats=True,with_invited_chats=False)
            if not isinstance(groups,dict) or not isinstance(groups.get('memberChatMids'),list):
                raise ValueError('line_groups_shape_unknown')
            joined=list(dict.fromkeys(groups['memberChatMids']))
            if joined:
                contacts.extend(normalize_groups(self.api.get_chats(joined,with_members=True,with_invitees=False),set(joined)))
            self.store.refresh_contacts(contacts)
            log_event(logging.getLogger('sweety.line'), 'line_directory_refreshed',
                      contact_ids=len(ids), blocked_ids=len(blocked),
                      response_contacts=len(response.get('contacts', {})),
                      normalized_people=sum(c.get('kind', 'person') == 'person' for c in contacts),
                      joined_groups=len(joined), stored_contacts=len(self.store.contacts()))
        return self.store.contacts()

    def decode(self,raw):
        with self.lock:
            if not self.connected(): raise ValueError('line_login_required')
            return self.api.decrypt_message(raw) if raw.get('chunks') else raw

    def history_for_reply(self,target_id,limit,*,exclude_ids,before,allowed=lambda:True):
        from .line_history import read_history
        from .okline_errors import LineHistoryError
        try:
            with self.lock:
                if not self.connected() or not allowed():
                    raise LineHistoryError('history_cancelled')
                target=self.repo.get_target(target_id)
                if target not in self.store.targets():
                    raise LineHistoryError('history_target_unavailable')
                return read_history(self.api,target,self.store.account,limit,set(exclude_ids),
                    before,self.decode,allowed)
        except LineHistoryError:
            raise
        except Exception as exc:
            raise LineHistoryError('line_history_unavailable') from exc

    def image_inputs(self, raw, *, allowed=lambda: True):
        from .visual_media import download_image, download_sticker, encode_images, MediaError
        with self.lock:
            if not self.connected() or not allowed():
                raise MediaError('media_cancelled')
            kind=int(raw.get('contentType') or 0)
            if kind==1:
                payload=download_image(self.api,raw)
            elif kind==7:
                payload=download_sticker(raw)
            else:
                raise MediaError('media_type_unsupported')
        if not allowed():
            raise MediaError('media_cancelled')
        return encode_images(payload)

    def send(self, target_id, text, *, allowed=lambda: True, expected_scope=None):
        with self.lock:
            if not self.connected() or not allowed():
                raise SendNotStarted('line_send_cancelled')
            if expected_scope is not None and expected_scope != self.store.scope:
                raise SendNotStarted('line_account_changed')
            target = self.repo.get_target(target_id)
            contact = self.store.contact(target.get('line_mid', ''))
            if (target not in self.store.targets() or contact['blocked'] or not text.strip()):
                raise SendNotStarted('line_send_cancelled')
            if not allowed():
                raise SendNotStarted('line_send_cancelled')
            result = self.api.send_text(target['line_mid'], text)
            message = result.get('message', result) if isinstance(result, dict) else {}
            if not isinstance(message, dict) or not message.get('id'):
                raise ValueError('line_receipt_uncertain')
            return str(message['id'])

    def ingest(self, message, revision=None, *, stop=None):
        with self.lock:
            if (not self.allow_receiving() or not self.connected() or
                    (stop is not None and stop.is_set())):
                return False
            # Call signalling never becomes chat input. Media stays metadata-only.
            meta = message.get('contentMetadata') or {}
            if int(message.get('contentType') or 0) == 6 or meta.get('CALLTYPE'):
                self.store.advance(revision)
                return False
            decoded = self.decode(message)
            inserted = self.store.ingest(decoded, revision,
                context_only=int(decoded.get('createdTime') or 0) < int(self.receive_cutoff * 1000))
            self.wake.set()
            return inserted

    def archive_pending(self):
        self.store.archive_pending()

    def prepare_receiving(self, cutoff):
        self.receive_cutoff = cutoff
        self.store.since = int(cutoff * 1000)
        self.stop_stream = threading.Event()

    def start_receiving(self):
        if not self.allow_receiving():
            return
        if self.stream_thread and self.stream_thread.is_alive():
            if self.stream_token is not None and not self.stream_token.is_set():
                return
            self.stream_thread.join(timeout=1)
            if self.stream_thread.is_alive():
                raise ValueError('line_receiver_stopping')
        with self.lock:
            if not self.connected():
                raise ValueError('line_login_required')
            revision = self.api.get_last_op_revision()
            self.store.advance(revision)
            self.stream_token = self.stop_stream
        self.stream_thread = threading.Thread(target=self._receive,
            args=(self.generation, self.stop_stream), daemon=True, name='Sweety-LineEvents')
        self.stream_thread.start()

    def stop_receiving(self):
        self.stop_stream.set()
        self.wake.set()
        if self.receiver:
            self.receiver.ops.request_reconnect()

    def reconcile_history(self, stop):
        """Paginate selected conversations back to this run's cutover, before advancing sync."""
        for target in self.store.targets():
            with self.lock:
                if stop.is_set() or not self.allow_receiving():
                    return
                page = message_list(self.api.get_recent_messages(target['line_mid'], 50))
            found = {}; visited = set()
            for _ in range(100):
                if stop.is_set() or not self.allow_receiving():
                    return
                if not page:
                    break
                stamps = [int(m.get('createdTime') or 0) for m in page]
                if not all(stamps):
                    raise ValueError('line_history_time_missing')
                for message in page:
                    if int(message['createdTime']) >= self.store.since:
                        found[str(message['id'])] = message
                oldest = min(page, key=lambda m: int(m['createdTime']))
                if int(oldest['createdTime']) < self.store.since:
                    break
                cursor = str(oldest['id'])
                if cursor in visited:
                    raise ValueError('line_history_pagination_stalled')
                visited.add(cursor)
                with self.lock:
                    if stop.is_set():
                        return
                    page = message_list(self.api.get_previous_messages(target['line_mid'],
                        end_message_id=cursor, delivered_time=int(oldest.get('deliveredTime') or oldest['createdTime']), count=50))
            else:
                raise ValueError('line_history_limit')
            for message in sorted(found.values(), key=lambda m: (int(m['createdTime']), str(m['id']))):
                self.ingest(message, stop=stop)

    def _receive(self, generation, stop):
        delay = 1
        while not stop.is_set() and generation == self.generation and self.connected():
            receiver = None
            try:
                with self.lock:
                    receiver = sdk_factory()
                    receiver.transport.tokens = self.api.transport.tokens
                    receiver.transport._refresh_hook = self.api._auto_refresh
                    receiver.ops.local_rev = self.store.cursor()
                    self.receiver = receiver
                self.reconcile_history(stop)
                for event in receiver.ops.stream(reconnect=False, keepalive=True):
                    if stop.is_set() or generation != self.generation or not self.allow_receiving():
                        return
                    if event.event in {'fullSync', 'partialFullSync'}:
                        self.reconcile_history(stop)
                        if stop.is_set():
                            return
                        revision = event.data.get('nextRevision') if isinstance(event.data, dict) else None
                        self.store.advance(revision)
                        receiver.ops.local_rev = self.store.cursor()
                        continue
                    payload = event.data
                    operations = payload.get('operations', [payload]) if isinstance(payload, dict) else payload
                    if not isinstance(operations, list):
                        continue
                    for op in operations:
                        if stop.is_set() or generation != self.generation or not self.allow_receiving():
                            return
                        if not isinstance(op, dict):
                            continue
                        revision = op.get('revision')
                        if int(op.get('type') or 0) in (25, 26) and op.get('message'):
                            self.ingest(op['message'], revision, stop=stop)
                        else:
                            self.store.advance(revision)
                        if revision is not None:
                            receiver.ops.local_rev = int(revision)
                    delay = 1
                    self.state['streamError'] = ''
                # A clean SSE EOF also needs backoff; avoid rapid history/network loops.
                if stop.wait(delay):
                    return
                delay = min(delay * 2, 30)
            except Exception as exc:
                if stop.is_set() or generation != self.generation or not self.allow_receiving():
                    return
                self.state['streamError'] = 'line_reconnecting: ' + type(exc).__name__
                if stop.wait(delay):
                    return
                delay = min(delay * 2, 30)
            finally:
                if receiver:
                    receiver.close()
                if self.receiver is receiver:
                    self.receiver = None
