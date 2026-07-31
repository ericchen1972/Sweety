from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import pytest

from sweety_app.ai import AiError, ReplyDecision
from sweety_app.database import Database
from sweety_app.diagnostics import configure_diagnostics
from sweety_app.monitor import MonitorController, UnreadContact, match_unread_target
from sweety_app.repositories import Repository


@pytest.fixture
def repo(tmp_path):
    database = Database(tmp_path / "monitor.sqlite3")
    database.migrate()
    return Repository(database)


@pytest.fixture
def diagnostics_enabled(tmp_path):
    configure_diagnostics(tmp_path / "sweety.log", enabled=True)
    yield
    configure_diagnostics(tmp_path / "sweety.log", enabled=False)


def target_payload(name: str, reply_enabled: bool = True) -> dict:
    return {
        "name": name,
        "age_group": "20-35",
        "gender": "female",
        "persona_id": "cautious-accounting-assistant",
        "persona_source": "base",
        "weapon_id": "one-step-at-a-time",
        "weapon_source": "base",
        "reply_enabled": reply_enabled,
    }


class FakeLine:
    def __init__(
        self,
        contacts: list[UnreadContact],
        main_window: bool = True,
        send_success: bool = True,
        cleanup_success: bool = True,
        capture_cleanup_result: str = "discarded",
    ) -> None:
        self.contacts = contacts
        self.main_window = main_window
        self.send_success = send_success
        self.cleanup_success = cleanup_success
        self.capture_cleanup_result = capture_cleanup_result
        self.opened: list[str] = []
        self.sent: list[tuple[str, str]] = []
        self.closed = 0
        self.events: list[str] = []
        self.discarded: list[Path] = []

    def main_window_exists(self) -> bool:
        return self.main_window

    def unread_contacts(self) -> list[UnreadContact]:
        self.events.append("unread_contacts")
        return self.contacts

    def close_other_chat_windows(self) -> bool:
        self.events.append("cleanup")
        return self.cleanup_success

    def open_chat(self, contact: UnreadContact) -> bool:
        self.opened.append(contact.name)
        self.events.append(f"open:{contact.name}")
        return True

    def prepare_next_chat(self) -> bool:
        self.events.append("prepare_next_chat")
        return True

    def capture_visible_chat(self, target_name: str) -> Path:
        assert target_name in self.opened
        self.events.append("capture")
        return Path("/tmp/test-line-chat.png")

    def discard_chat_capture(self, screenshot_path: Path) -> str:
        self.events.append("discard")
        self.discarded.append(screenshot_path)
        return self.capture_cleanup_result

    def send_message(self, target_name: str, reply: str) -> bool:
        assert target_name in self.opened
        self.events.append("send")
        self.sent.append((target_name, reply))
        return self.send_success

    def close_chat(self, target_name: str) -> None:
        assert target_name in self.opened
        self.closed += 1


@dataclass
class FakeAi:
    decision: ReplyDecision = ReplyDecision(
        action="reply",
        incoming_summary="你還記得那個網站嗎？",
        msg_reply="我有點忘了，是哪個？",
    )

    def generate_reply(self, **_kwargs) -> ReplyDecision:
        return self.decision


def test_unread_matching_prefers_exact_name_and_has_limited_ocr_fallback():
    targets = [{"name": "💖Lilian✨", "id": "a"}, {"name": "Lilian", "id": "b"}]
    exact = match_unread_target(UnreadContact(index=1, name="Lilian"), targets)
    fallback = match_unread_target(UnreadContact(index=2, name="💖Lilian"), [targets[0]])

    assert exact["id"] == "b"
    assert fallback["id"] == "a"


def test_cycle_ignores_unchecked_and_ended_targets(repo):
    repo.create_target(target_payload("未勾選", reply_enabled=False))
    ended = repo.create_target(target_payload("已結束"))
    repo.end_target(ended["id"])
    line = FakeLine([UnreadContact(index=0, name="未勾選"), UnreadContact(index=1, name="已結束")])
    controller = MonitorController(repo, line, FakeAi(), sleeper=lambda _seconds: None)

    assert controller.run_cycle() is False
    assert line.opened == []
    assert line.sent == []


def test_cycle_cleans_up_other_chat_windows_before_unread_scan(repo):
    repo.create_target(target_payload("投資顧問"))
    line = FakeLine([])
    controller = MonitorController(repo, line, FakeAi(), sleeper=lambda _seconds: None)

    controller.run_cycle()

    assert line.events[:2] == ["cleanup", "unread_contacts"]


def test_cycle_continues_unread_scan_when_pre_scan_cleanup_fails(repo):
    repo.create_target(target_payload("投資顧問"))
    line = FakeLine([], cleanup_success=False)
    controller = MonitorController(repo, line, FakeAi(), sleeper=lambda _seconds: None)

    assert controller.run_cycle() is False
    assert line.events == ["cleanup", "unread_contacts"]


def test_cycle_prepares_line_main_window_before_opening_second_contact(repo):
    repo.create_target(target_payload("Eva"))
    repo.create_target(target_payload("Rose"))
    line = FakeLine(
        [
            UnreadContact(index=1, name="Eva"),
            UnreadContact(index=2, name="Rose"),
        ]
    )
    controller = MonitorController(repo, line, FakeAi(), sleeper=lambda _seconds: None)
    controller.start(background=False)

    assert controller.run_cycle() is True
    assert line.events.index("open:Eva") < line.events.index("prepare_next_chat")
    assert line.events.index("prepare_next_chat") < line.events.index("open:Rose")
    assert line.events.count("prepare_next_chat") == 1


def test_live_mode_sends_and_persists_exchange_and_metrics(repo):
    target = repo.create_target(target_payload("投資顧問✨"))
    line = FakeLine([UnreadContact(index=0, name="投資顧問✨")])
    controller = MonitorController(repo, line, FakeAi(), sleeper=lambda _seconds: None)

    controller.start(background=False)
    processed = controller.run_cycle()

    assert processed is True
    assert line.opened == ["投資顧問✨"]
    assert line.sent == [("投資顧問✨", "我有點忘了，是哪個？")]
    assert line.closed == 1
    assert line.discarded == [Path("/tmp/test-line-chat.png")]
    assert line.events.index("discard") < line.events.index("send")
    assert [(item["role"], item["content"]) for item in repo.list_messages(target["id"])] == [
        ("scammer", "你還記得那個網站嗎？"),
        ("assistant", "我有點忘了，是哪個？"),
    ]
    assert repo.get_target(target["id"])["round_trips"] == 1
    assert controller.snapshot()["enabled"] is True
    assert controller.snapshot()["testMode"] is False


def test_send_failure_does_not_persist_or_count(repo):
    target = repo.create_target(target_payload("投資顧問"))
    line = FakeLine([UnreadContact(index=1, name="投資顧問")], send_success=False)
    controller = MonitorController(repo, line, FakeAi(), sleeper=lambda _seconds: None)
    controller.start(background=False)

    assert controller.run_cycle() is False
    assert repo.list_messages(target["id"]) == []
    assert repo.get_target(target["id"])["round_trips"] == 0
    assert line.discarded == [Path("/tmp/test-line-chat.png")]


def test_mixed_visible_batch_is_persisted_as_one_exchange_after_successful_send(repo):
    target = repo.create_target(target_payload("投資顧問"))
    line = FakeLine([UnreadContact(index=1, name="投資顧問")])
    ai = FakeAi(
        ReplyDecision(
            action="reply",
            incoming_summary="對方先問網站進度，接著傳了一張貼圖，最後補上一張版面截圖",
            msg_reply="有看到，我先照截圖調整版面，再跟你回報。",
        )
    )
    controller = MonitorController(repo, line, ai, sleeper=lambda _seconds: None)
    controller.start(background=False)

    assert controller.run_cycle() is True
    assert [(item["role"], item["content"]) for item in repo.list_messages(target["id"])] == [
        ("scammer", "對方先問網站進度，接著傳了一張貼圖，最後補上一張版面截圖"),
        ("assistant", "有看到，我先照截圖調整版面，再跟你回報。"),
    ]


def test_skip_discards_capture_and_does_not_delay_send_persist_count_or_report(repo):
    target = repo.create_target(target_payload("投資顧問"))
    line = FakeLine([UnreadContact(index=1, name="投資顧問")])
    delays: list[float] = []
    reports: list[bool] = []
    controller = MonitorController(
        repo,
        line,
        FakeAi(ReplyDecision(action="skip", incoming_summary="", msg_reply="")),
        sleeper=lambda seconds: delays.append(seconds),
        on_exchange_committed=lambda: reports.append(True),
    )
    controller.start(background=False)

    assert controller.run_cycle() is False
    assert line.discarded == [Path("/tmp/test-line-chat.png")]
    assert line.closed == 1
    assert delays == []
    assert line.sent == []
    assert repo.list_messages(target["id"]) == []
    assert repo.get_target(target["id"])["round_trips"] == 0
    assert reports == []


def test_skip_logs_ai_decision_and_close_reason(repo, caplog, diagnostics_enabled):
    repo.create_target(target_payload("Rose"))
    logger = logging.getLogger("test.sweety.monitor.skip")
    controller = MonitorController(
        repo,
        FakeLine([UnreadContact(index=1, name="Rose")]),
        FakeAi(ReplyDecision(action="skip", incoming_summary="", msg_reply="")),
        sleeper=lambda _seconds: None,
        logger=logger,
    )
    controller.start(background=False)

    with caplog.at_level(logging.INFO, logger=logger.name):
        assert controller.run_cycle() is False

    events = [json.loads(record.message) for record in caplog.records if record.name == logger.name]
    ai_event = next(event for event in events if event["event"] == "ai_request_succeeded")
    assert ai_event["target"] == "Rose"
    assert ai_event["action"] == "skip"
    assert ai_event["incoming_summary"] == ""
    assert ai_event["msg_reply"] == ""
    assert any(
        event["event"] == "chat_close_started" and event["reason"] == "ai_decision_skip"
        for event in events
    )


def test_successful_committed_exchange_triggers_metrics_report_once(repo):
    target = repo.create_target(target_payload("投資顧問"))
    line = FakeLine([UnreadContact(index=1, name="投資顧問")])
    reports: list[int] = []
    controller = MonitorController(
        repo,
        line,
        FakeAi(),
        sleeper=lambda _seconds: None,
        on_exchange_committed=lambda: reports.append(len(repo.list_messages(target["id"]))),
    )
    controller.start(background=False)

    assert controller.run_cycle() is True
    assert reports == [2]


def test_successful_cycle_logs_stage_events_and_ai_decision(repo, caplog, diagnostics_enabled):
    target = repo.create_target(target_payload("Rose"))
    line = FakeLine([UnreadContact(index=1, name="Rose")])
    logger = logging.getLogger("test.sweety.monitor.success")
    controller = MonitorController(
        repo,
        line,
        FakeAi(ReplyDecision(action="reply", incoming_summary="對方最後一則訊息", msg_reply="這是我的回覆")),
        sleeper=lambda _seconds: None,
        logger=logger,
    )
    controller.start(background=False)

    with caplog.at_level(logging.INFO, logger=logger.name):
        assert controller.run_cycle() is True

    events = [json.loads(record.message) for record in caplog.records if record.name == logger.name]
    names = [event["event"] for event in events]
    assert names == [
        "cycle_started",
        "chat_cleanup_started",
        "chat_cleanup_succeeded",
        "unread_scan_started",
        "unread_scan_succeeded",
        "target_processing_started",
        "chat_open_started",
        "chat_open_succeeded",
        "screenshot_capture_started",
        "screenshot_capture_succeeded",
        "ai_request_started",
        "ai_request_succeeded",
        "screenshot_discarded",
        "reply_delay_started",
        "reply_delay_completed",
        "message_send_started",
        "message_send_succeeded",
        "exchange_persist_started",
        "exchange_persist_succeeded",
        "chat_close_started",
        "chat_close_succeeded",
        "cycle_completed",
    ]
    ai_event = next(event for event in events if event["event"] == "ai_request_succeeded")
    assert {key: ai_event[key] for key in ("event", "target", "action", "incoming_summary", "msg_reply")} == {
        "event": "ai_request_succeeded",
        "target": "Rose",
        "action": "reply",
        "incoming_summary": "對方最後一則訊息",
        "msg_reply": "這是我的回覆",
    }
    assert ai_event["timestamp"].endswith("+00:00")
    assert repo.get_target(target["id"])["round_trips"] == 1


def test_diagnostic_cycle_logs_retained_screenshot_path(repo, caplog, diagnostics_enabled):
    repo.create_target(target_payload("Rose"))
    line = FakeLine(
        [UnreadContact(index=1, name="Rose")],
        capture_cleanup_result="retained",
    )
    logger = logging.getLogger("test.sweety.monitor.retained")
    controller = MonitorController(
        repo,
        line,
        FakeAi(ReplyDecision(action="skip", incoming_summary="", msg_reply="")),
        sleeper=lambda _seconds: None,
        logger=logger,
    )
    controller.start(background=False)

    with caplog.at_level(logging.INFO, logger=logger.name):
        assert controller.run_cycle() is False

    events = [json.loads(record.message) for record in caplog.records if record.name == logger.name]
    retained = next(event for event in events if event["event"] == "screenshot_retained")
    assert retained["target"] == "Rose"
    assert retained["path"] == "/tmp/test-line-chat.png"
    assert all(event["event"] != "screenshot_discarded" for event in events)


def test_failed_send_does_not_trigger_metrics_report(repo):
    repo.create_target(target_payload("投資顧問"))
    line = FakeLine([UnreadContact(index=1, name="投資顧問")], send_success=False)
    reports: list[bool] = []
    controller = MonitorController(
        repo,
        line,
        FakeAi(),
        sleeper=lambda _seconds: None,
        on_exchange_committed=lambda: reports.append(True),
    )
    controller.start(background=False)

    assert controller.run_cycle() is False
    assert reports == []


def test_committed_exchange_is_reported_even_when_close_chat_fails(repo):
    target = repo.create_target(target_payload("投資顧問"))
    reports: list[int] = []

    class CloseFailureLine(FakeLine):
        def close_chat(self, target_name: str) -> None:
            super().close_chat(target_name)
            raise RuntimeError("LINE window disappeared after send")

    controller = MonitorController(
        repo,
        CloseFailureLine([UnreadContact(index=1, name="投資顧問")]),
        FakeAi(),
        sleeper=lambda _seconds: None,
        on_exchange_committed=lambda: reports.append(len(repo.list_messages(target["id"])),),
    )
    controller.start(background=False)

    assert controller.run_cycle() is True
    assert reports == [2]
    assert repo.get_target(target["id"])["round_trips"] == 1


def test_cycle_processes_every_matching_unread_target(repo):
    first = repo.create_target(target_payload("對象 A"))
    second = repo.create_target(target_payload("對象 B"))
    line = FakeLine([UnreadContact(index=1, name="對象 A"), UnreadContact(index=2, name="對象 B")])
    controller = MonitorController(repo, line, FakeAi(), sleeper=lambda _seconds: None)
    controller.start(background=False)

    assert controller.run_cycle() is True
    assert [name for name, _reply in line.sent] == ["對象 A", "對象 B"]
    assert repo.get_target(first["id"])["round_trips"] == 1
    assert repo.get_target(second["id"])["round_trips"] == 1


def test_start_and_stop_are_idempotent(repo):
    repo.create_target(target_payload("已勾選"))
    line = FakeLine([])
    controller = MonitorController(repo, line, FakeAi(), sleeper=lambda _seconds: None)

    assert controller.start(background=False) is True
    assert controller.start(background=False) is False
    assert controller.stop() is True
    assert controller.stop() is False


def test_restart_does_not_clear_the_previous_run_stop_signal(repo):
    repo.create_target(target_payload("已勾選"))
    controller = MonitorController(repo, FakeLine([]), FakeAi(), sleeper=lambda _seconds: None)

    controller.start(background=False)
    previous_run_stop = controller._stop_event
    controller.stop()
    controller.start(background=False)

    assert previous_run_stop.is_set()
    assert controller._stop_event is not previous_run_stop


def test_stop_after_chat_capture_prevents_ai_and_paste(repo):
    repo.create_target(target_payload("投資顧問"))
    calls = []
    controller = None

    class StopAfterCaptureLine(FakeLine):
        def capture_visible_chat(self, target_name: str) -> Path:
            controller.stop()
            return super().capture_visible_chat(target_name)

    class RecordingAi(FakeAi):
        def generate_reply(self, **kwargs) -> ReplyDecision:
            calls.append(kwargs)
            return super().generate_reply(**kwargs)

    line = StopAfterCaptureLine([UnreadContact(index=1, name="投資顧問")])
    controller = MonitorController(repo, line, RecordingAi(), sleeper=lambda _seconds: None)
    controller.start(background=False)

    assert controller.run_cycle() is False
    assert calls == []
    assert line.sent == []
    assert line.discarded == [Path("/tmp/test-line-chat.png")]


def test_ai_failure_does_not_send_or_persist(repo, caplog, diagnostics_enabled):
    target = repo.create_target(target_payload("投資顧問"))
    line = FakeLine([UnreadContact(index=1, name="投資顧問")])
    reports: list[bool] = []

    class FailingAi:
        def generate_reply(self, **_kwargs):
            raise AiError("AI returned an invalid reply")

    logger = logging.getLogger("test.sweety.monitor.ai_failure")
    controller = MonitorController(
        repo,
        line,
        FailingAi(),
        sleeper=lambda _seconds: None,
        on_exchange_committed=lambda: reports.append(True),
        logger=logger,
    )
    controller.start(background=False)

    with caplog.at_level(logging.INFO, logger=logger.name):
        assert controller.run_cycle() is False
    assert line.sent == []
    assert repo.list_messages(target["id"]) == []
    assert repo.get_target(target["id"])["round_trips"] == 0
    assert reports == []
    assert line.discarded == [Path("/tmp/test-line-chat.png")]
    events = [json.loads(record.message) for record in caplog.records if record.name == logger.name]
    failure = next(event for event in events if event["event"] == "target_processing_failed")
    assert failure["target"] == "投資顧問"
    assert failure["stage"] == "ai_request"
    assert failure["error_type"] == "AiError"
    assert failure["error"] == "AI returned an invalid reply"


def test_capture_failure_does_not_call_ai_send_persist_or_report(repo):
    target = repo.create_target(target_payload("投資顧問"))
    reports: list[bool] = []
    ai_calls: list[bool] = []

    class CaptureFailureLine(FakeLine):
        def capture_visible_chat(self, target_name: str) -> Path:
            raise RuntimeError("screen capture denied")

    class RecordingAi(FakeAi):
        def generate_reply(self, **kwargs) -> ReplyDecision:
            ai_calls.append(True)
            return super().generate_reply(**kwargs)

    line = CaptureFailureLine([UnreadContact(index=1, name="投資顧問")])
    controller = MonitorController(
        repo,
        line,
        RecordingAi(),
        sleeper=lambda _seconds: None,
        on_exchange_committed=lambda: reports.append(True),
    )
    controller.start(background=False)

    assert controller.run_cycle() is False
    assert ai_calls == []
    assert line.sent == []
    assert repo.list_messages(target["id"]) == []
    assert repo.get_target(target["id"])["round_trips"] == 0
    assert reports == []


def test_stop_after_delay_before_send_keeps_stopped_state_and_persists_nothing(repo):
    target = repo.create_target(target_payload("投資顧問"))
    line = FakeLine([UnreadContact(index=1, name="投資顧問")])
    controller = MonitorController(repo, line, FakeAi(), sleeper=lambda _seconds: None)
    controller.start(background=False)

    def stop_after_delay(_seconds, _stop_event=None):
        controller.stop()
        return True

    controller._interruptible_sleep = stop_after_delay

    assert controller.run_cycle() is False
    assert line.sent == []
    assert repo.list_messages(target["id"]) == []
    assert repo.get_target(target["id"])["round_trips"] == 0
    assert line.discarded == [Path("/tmp/test-line-chat.png")]
    assert controller.snapshot()["status"] == "stopped"


def test_missing_permissions_keep_monitor_stopped(repo):
    controller = MonitorController(repo, FakeLine([]), FakeAi(), automation_allowed=False)

    assert controller.start(background=False) is False
    assert controller.snapshot()["enabled"] is False
    assert controller.snapshot()["status"] == "permission_required"


def test_region_block_keeps_monitor_stopped(repo):
    repo.create_target(target_payload("已勾選"))
    controller = MonitorController(repo, FakeLine([]), FakeAi(), region_blocked=True)

    assert controller.start(background=False) is False
    assert controller.snapshot()["enabled"] is False
    assert controller.snapshot()["status"] == "region_blocked"


def test_start_requires_line_main_window(repo):
    repo.create_target(target_payload("已勾選"))
    controller = MonitorController(repo, FakeLine([], main_window=False), FakeAi())

    assert controller.start(background=False) is False
    assert controller.snapshot()["enabled"] is False
    assert controller.snapshot()["status"] == "line_window_required"


def test_start_requires_an_enabled_target(repo):
    repo.create_target(target_payload("未勾選", reply_enabled=False))
    controller = MonitorController(repo, FakeLine([]), FakeAi())

    assert controller.start(background=False) is False
    assert controller.snapshot()["enabled"] is False
    assert controller.snapshot()["status"] == "target_required"
