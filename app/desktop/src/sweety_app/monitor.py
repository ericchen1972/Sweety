from __future__ import annotations

import logging
import random
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from .ai import ReplyDecision
from .diagnostics import log_event
from .repositories import Repository


@dataclass(frozen=True)
class UnreadContact:
    index: int
    name: str


class LineAdapter(Protocol):
    def main_window_exists(self) -> bool: ...
    def unread_contacts(self) -> list[UnreadContact]: ...
    def prepare_next_chat(self) -> bool: ...
    def open_chat(self, contact: UnreadContact) -> bool: ...
    def capture_visible_chat(self, target_name: str) -> Path: ...
    def discard_chat_capture(self, screenshot_path: Path) -> str: ...
    def send_message(self, target_name: str, reply: str) -> bool: ...
    def close_chat(self, target_name: str) -> bool: ...
    def close_other_chat_windows(self) -> bool: ...


class AiAdapter(Protocol):
    def generate_reply(self, **kwargs: Any) -> ReplyDecision: ...


def _match_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def match_unread_target(contact: UnreadContact, targets: list[dict[str, Any]]) -> dict[str, Any] | None:
    contact_key = _match_key(contact.name)
    exact = next((target for target in targets if _match_key(str(target["name"])) == contact_key), None)
    if exact is not None:
        return exact

    candidates = [
        target
        for target in targets
        if contact_key and (
            contact_key in _match_key(str(target["name"]))
            or _match_key(str(target["name"])) in contact_key
        )
    ]
    return candidates[0] if len(candidates) == 1 else None


class MonitorController:
    def __init__(
        self,
        repository: Repository,
        line: LineAdapter,
        ai: AiAdapter,
        sleeper: Callable[[float], None] = time.sleep,
        automation_allowed: bool = True,
        region_blocked: bool = False,
        on_exchange_committed: Callable[[], None] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.repository = repository
        self.line = line
        self.ai = ai
        self.sleeper = sleeper
        self.automation_allowed = automation_allowed
        self.region_blocked = region_blocked
        self.on_exchange_committed = on_exchange_committed
        self.logger = logger or logging.getLogger("sweety.monitor")
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._enabled = False
        self._status = "stopped"
        self._message = ""
        self._current_target: str | None = None

    def start(self, background: bool = True) -> bool:
        self._log("monitor_start_requested", background=background)
        with self._lock:
            if self.region_blocked:
                self._enabled = False
                self._status = "region_blocked"
                self._message = "region_blocked"
                self._log("monitor_start_rejected", reason="region_blocked")
                return False
            if not self.automation_allowed:
                self._enabled = False
                self._status = "permission_required"
                self._message = "macos_permissions_required"
                self._log("monitor_start_rejected", reason="macos_permissions_required")
                return False
            try:
                if not self.line.main_window_exists():
                    self._enabled = False
                    self._status = "line_window_required"
                    self._message = "line_main_window_not_found"
                    self._log("monitor_start_rejected", reason="line_main_window_not_found")
                    return False
            except Exception as exc:
                self._enabled = False
                self._status = "line_window_required"
                self._message = "line_main_window_not_found"
                self._log(
                    "monitor_start_rejected",
                    level=logging.ERROR,
                    reason="line_main_window_check_failed",
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                return False
            if not self.repository.list_monitor_targets():
                self._enabled = False
                self._status = "target_required"
                self._message = "no_enabled_targets"
                self._log("monitor_start_rejected", reason="no_enabled_targets")
                return False
            if self._enabled or (self._thread is not None and self._thread.is_alive()):
                self._log("monitor_start_rejected", reason="already_running")
                return False
            self._stop_event = threading.Event()
            self._enabled = True
            self._status = "monitoring"
            self._message = ""
            self._current_target = None
            if background:
                stop_event = self._stop_event
                self._thread = threading.Thread(
                    target=self._run_loop,
                    args=(stop_event,),
                    name="SweetyLineMonitor",
                    daemon=True,
                )
                self._thread.start()
        self._log("monitor_started", background=background)
        return True

    def stop(self) -> bool:
        self._log("monitor_stop_requested")
        with self._lock:
            was_enabled = self._enabled
            self._enabled = False
            self._stop_event.set()
            if was_enabled:
                self._status = "stopped"
                self._message = ""
                self._current_target = None
            self._log("monitor_stopped", was_enabled=was_enabled)
            return was_enabled

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled": self._enabled,
                "testMode": False,
                "status": self._status,
                "message": self._message,
                "currentTarget": self._current_target,
                "selectedTargetCount": len(self.repository.list_monitor_targets()),
            }

    def run_cycle(self, stop_event: threading.Event | None = None) -> bool:
        run_stop = stop_event or self._stop_event
        targets = self.repository.list_monitor_targets()
        self._log("cycle_started", target_count=len(targets))
        if not targets:
            self._set_status("waiting", "no_enabled_targets")
            self._log("cycle_completed", processed_any=False, reason="no_enabled_targets")
            return False

        self._log("chat_cleanup_started")
        try:
            cleanup_result = self.line.close_other_chat_windows()
            self._log("chat_cleanup_succeeded", result=bool(cleanup_result))
        except Exception as exc:
            self._log(
                "chat_cleanup_failed",
                level=logging.ERROR,
                error_type=type(exc).__name__,
                error=str(exc),
            )

        self._log("unread_scan_started")
        try:
            contacts = self.line.unread_contacts()
        except Exception as exc:
            self._set_status("error", f"unread_scan_failed: {exc}")
            self._log(
                "unread_scan_failed",
                level=logging.ERROR,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            self._log("cycle_completed", processed_any=False, reason="unread_scan_failed")
            return False
        self._log(
            "unread_scan_succeeded",
            contact_count=len(contacts),
            contacts=[contact.name for contact in contacts],
        )

        processed_any = False
        matched_contact_count = 0
        for contact in contacts:
            if run_stop.is_set():
                self._log("cycle_interrupted", stage="before_target_match")
                return False
            target = match_unread_target(contact, targets)
            if target is None:
                self._log("target_not_matched", contact=contact.name, contact_index=contact.index)
                continue

            target_name = str(target["name"])
            if matched_contact_count:
                self._log("next_chat_prepare_started", target=target_name)
                if not self.line.prepare_next_chat():
                    self._set_status("error", "prepare_next_chat_failed", target_name)
                    self._log("next_chat_prepare_failed", level=logging.ERROR, target=target_name)
                    continue
                self._log("next_chat_prepare_succeeded", target=target_name)
            matched_contact_count += 1
            self._set_status("processing", "", target_name)
            self._log("target_processing_started", target=target_name, contact_index=contact.index)
            stage = "target_processing_started"
            try:
                stage = "chat_open"
                self._log("chat_open_started", target=target_name)
                if not self.line.open_chat(contact):
                    self._set_status("error", "open_chat_failed", target_name)
                    self._log("chat_open_failed", level=logging.ERROR, target=target_name)
                    continue
                self._log("chat_open_succeeded", target=target_name)
                if run_stop.is_set():
                    self._log("target_interrupted", target=target_name, stage="after_chat_open")
                    self._close_chat(target_name, "stop_after_chat_open")
                    return False
                stage = "screenshot_capture"
                self._log("screenshot_capture_started", target=target_name)
                screenshot_path = self.line.capture_visible_chat(target_name)
                self._log("screenshot_capture_succeeded", target=target_name)
                try:
                    if run_stop.is_set():
                        self._log("target_interrupted", target=target_name, stage="after_screenshot_capture")
                        self._close_chat(target_name, "stop_after_screenshot_capture")
                        return False
                    settings = self.repository.get_settings()
                    history = self.repository.list_messages(str(target["id"]), limit=20)
                    total_messages = len(self.repository.list_messages(str(target["id"])))
                    stage = "ai_request"
                    self._log(
                        "ai_request_started",
                        target=target_name,
                        history_count=len(history),
                        total_messages=total_messages,
                    )
                    decision = self.ai.generate_reply(
                        target=target,
                        screenshot_path=screenshot_path,
                        history=history,
                        total_messages=total_messages,
                        settings=settings,
                    )
                    self._log(
                        "ai_request_succeeded",
                        target=target_name,
                        action=decision.action,
                        incoming_summary=decision.incoming_summary,
                        msg_reply=decision.msg_reply,
                    )
                finally:
                    capture_cleanup = self.line.discard_chat_capture(screenshot_path)
                    if capture_cleanup == "retained":
                        self._log("screenshot_retained", target=target_name, path=str(screenshot_path))
                    else:
                        self._log("screenshot_discarded", target=target_name)
                if run_stop.is_set():
                    self._log("target_interrupted", target=target_name, stage="after_ai_request")
                    self._close_chat(target_name, "stop_after_ai_request")
                    return False
                if not decision.should_reply:
                    self._log("ai_decision_skipped", target=target_name, action=decision.action)
                    self._close_chat(target_name, "ai_decision_skip")
                    continue

                delay = random.uniform(
                    float(settings["reply_delay_min_seconds"]),
                    float(settings["reply_delay_max_seconds"]),
                )
                stage = "reply_delay"
                self._log("reply_delay_started", target=target_name, seconds=delay)
                if not self._interruptible_sleep(delay, run_stop):
                    self._log("reply_delay_interrupted", target=target_name, seconds=delay)
                    self._close_chat(target_name, "stop_during_reply_delay")
                    return processed_any
                self._log("reply_delay_completed", target=target_name, seconds=delay)
                if run_stop.is_set():
                    self._log("target_interrupted", target=target_name, stage="after_reply_delay")
                    self._close_chat(target_name, "stop_after_reply_delay")
                    return processed_any
                stage = "message_send"
                self._log("message_send_started", target=target_name)
                if not self.line.send_message(target_name, decision.msg_reply):
                    self._set_status("error", "send_failed", target_name)
                    self._log("message_send_failed", level=logging.ERROR, target=target_name)
                    self._close_chat(target_name, "message_send_failed")
                    continue
                self._log("message_send_succeeded", target=target_name)

                stage = "exchange_persist"
                self._log("exchange_persist_started", target=target_name)
                self.repository.record_exchange(
                    str(target["id"]),
                    decision.incoming_summary,
                    decision.msg_reply,
                )
                self._log("exchange_persist_succeeded", target=target_name)
                processed_any = True
                if self.on_exchange_committed is not None:
                    try:
                        self.on_exchange_committed()
                    except Exception as exc:
                        self._log(
                            "exchange_callback_failed",
                            level=logging.ERROR,
                            target=target_name,
                            error_type=type(exc).__name__,
                            error=str(exc),
                        )
                stage = "chat_close"
                self._close_chat(target_name, "exchange_completed")
            except Exception as exc:
                self._set_status("error", f"processing_failed: {exc}", target_name)
                self._log(
                    "target_processing_failed",
                    level=logging.ERROR,
                    exc_info=True,
                    target=target_name,
                    stage=stage,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                try:
                    self._close_chat(target_name, "processing_failed")
                except Exception as close_exc:
                    self._log(
                        "chat_close_recovery_failed",
                        level=logging.ERROR,
                        target=target_name,
                        error_type=type(close_exc).__name__,
                        error=str(close_exc),
                    )
                continue

        if processed_any:
            self._set_status("monitoring")
        else:
            self._set_status("waiting", "no_matching_unread")
        self._log("cycle_completed", processed_any=processed_any)
        return processed_any

    def _run_loop(self, stop_event: threading.Event) -> None:
        try:
            while not stop_event.is_set():
                processed = self.run_cycle(stop_event)
                if stop_event.is_set():
                    self._log("monitor_loop_stopped", stage="after_cycle")
                    return
                interval = float(self.repository.get_settings()["check_interval_seconds"])
                self._log("monitor_interval_started", seconds=interval, previous_cycle_processed=processed)
                if not self._interruptible_sleep(interval, stop_event):
                    self._log("monitor_interval_interrupted", seconds=interval)
                    return
                self._log("monitor_interval_completed", seconds=interval)
        finally:
            with self._lock:
                if self._thread is threading.current_thread():
                    self._thread = None

    def _close_chat(self, target_name: str, reason: str) -> bool:
        self._log("chat_close_started", target=target_name, reason=reason)
        try:
            result = self.line.close_chat(target_name)
        except Exception as exc:
            self._log(
                "chat_close_failed",
                level=logging.ERROR,
                exc_info=True,
                target=target_name,
                reason=reason,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise
        self._log("chat_close_succeeded", target=target_name, reason=reason, result=result)
        return result

    def _interruptible_sleep(self, seconds: float, stop_event: threading.Event | None = None) -> bool:
        run_stop = stop_event or self._stop_event
        seconds = max(0.0, seconds)
        if self.sleeper is time.sleep:
            return not run_stop.wait(seconds)
        self.sleeper(seconds)
        return not run_stop.is_set()

    def _set_status(self, status: str, message: str = "", target: str | None = None) -> None:
        with self._lock:
            self._status = status
            self._message = message
            self._current_target = target

    def _log(self, event: str, *, level: int = logging.INFO, exc_info: bool = False, **fields: Any) -> None:
        log_event(self.logger, event, level=level, exc_info=exc_info, **fields)
