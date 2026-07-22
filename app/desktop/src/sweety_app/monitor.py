from __future__ import annotations

import random
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .repositories import Repository


@dataclass(frozen=True)
class UnreadContact:
    index: int
    name: str


class LineAdapter(Protocol):
    def main_window_exists(self) -> bool: ...
    def unread_contacts(self) -> list[UnreadContact]: ...
    def open_chat(self, contact: UnreadContact) -> bool: ...
    def read_visible_chat(self, target_name: str) -> str: ...
    def send_message(self, target_name: str, reply: str) -> bool: ...
    def close_chat(self, target_name: str) -> None: ...


class AiAdapter(Protocol):
    def generate_reply(self, **kwargs: Any) -> str: ...


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
    ) -> None:
        self.repository = repository
        self.line = line
        self.ai = ai
        self.sleeper = sleeper
        self.automation_allowed = automation_allowed
        self.region_blocked = region_blocked
        self.on_exchange_committed = on_exchange_committed
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._enabled = False
        self._status = "stopped"
        self._message = ""
        self._current_target: str | None = None

    def start(self, background: bool = True) -> bool:
        with self._lock:
            if self.region_blocked:
                self._enabled = False
                self._status = "region_blocked"
                self._message = "region_blocked"
                return False
            if not self.automation_allowed:
                self._enabled = False
                self._status = "permission_required"
                self._message = "macos_permissions_required"
                return False
            try:
                if not self.line.main_window_exists():
                    self._enabled = False
                    self._status = "line_window_required"
                    self._message = "line_main_window_not_found"
                    return False
            except Exception:
                self._enabled = False
                self._status = "line_window_required"
                self._message = "line_main_window_not_found"
                return False
            if not self.repository.list_monitor_targets():
                self._enabled = False
                self._status = "target_required"
                self._message = "no_enabled_targets"
                return False
            if self._enabled or (self._thread is not None and self._thread.is_alive()):
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
        return True

    def stop(self) -> bool:
        with self._lock:
            was_enabled = self._enabled
            self._enabled = False
            self._stop_event.set()
            if was_enabled:
                self._status = "stopped"
                self._message = ""
                self._current_target = None
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
        if not targets:
            self._set_status("waiting", "no_enabled_targets")
            return False

        try:
            contacts = self.line.unread_contacts()
        except Exception as exc:
            self._set_status("error", f"unread_scan_failed: {exc}")
            return False

        processed_any = False
        for contact in contacts:
            if run_stop.is_set():
                return False
            target = match_unread_target(contact, targets)
            if target is None:
                continue

            self._set_status("processing", "", str(target["name"]))
            try:
                if not self.line.open_chat(contact):
                    self._set_status("error", "open_chat_failed", str(target["name"]))
                    continue
                if run_stop.is_set():
                    self.line.close_chat(str(target["name"]))
                    return False
                visible_text = self.line.read_visible_chat(str(target["name"]))
                if run_stop.is_set():
                    self.line.close_chat(str(target["name"]))
                    return False
                settings = self.repository.get_settings()
                history = self.repository.list_messages(str(target["id"]), limit=20)
                total_messages = len(self.repository.list_messages(str(target["id"])))
                reply = self.ai.generate_reply(
                    target=target,
                    visible_text=visible_text,
                    history=history,
                    total_messages=total_messages,
                    settings=settings,
                ).strip()
                if run_stop.is_set():
                    self.line.close_chat(str(target["name"]))
                    return False
                if not reply:
                    self.line.close_chat(str(target["name"]))
                    self._set_status("waiting", "empty_ai_reply")
                    continue

                delay = random.uniform(
                    float(settings["reply_delay_min_seconds"]),
                    float(settings["reply_delay_max_seconds"]),
                )
                if not self._interruptible_sleep(delay, run_stop):
                    self.line.close_chat(str(target["name"]))
                    return processed_any
                if run_stop.is_set() or not self.line.send_message(str(target["name"]), reply):
                    self._set_status("error", "send_failed", str(target["name"]))
                    self.line.close_chat(str(target["name"]))
                    continue

                self.repository.record_exchange(str(target["id"]), visible_text, reply)
                processed_any = True
                if self.on_exchange_committed is not None:
                    try:
                        self.on_exchange_committed()
                    except Exception:
                        pass
                self.line.close_chat(str(target["name"]))
            except Exception as exc:
                self._set_status("error", f"processing_failed: {exc}", str(target["name"]))
                try:
                    self.line.close_chat(str(target["name"]))
                except Exception:
                    pass
                continue

        if processed_any:
            self._set_status("monitoring")
        else:
            self._set_status("waiting", "no_matching_unread")
        return processed_any

    def _run_loop(self, stop_event: threading.Event) -> None:
        try:
            while not stop_event.is_set():
                processed = self.run_cycle(stop_event)
                if stop_event.is_set():
                    return
                interval = float(self.repository.get_settings()["check_interval_seconds"])
                if not self._interruptible_sleep(interval, stop_event):
                    return
        finally:
            with self._lock:
                if self._thread is threading.current_thread():
                    self._thread = None

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
