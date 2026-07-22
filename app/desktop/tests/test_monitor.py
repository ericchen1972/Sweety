from __future__ import annotations

from dataclasses import dataclass

import pytest

from sweety_app.database import Database
from sweety_app.monitor import MonitorController, UnreadContact, match_unread_target
from sweety_app.repositories import Repository


@pytest.fixture
def repo(tmp_path):
    database = Database(tmp_path / "monitor.sqlite3")
    database.migrate()
    return Repository(database)


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
    def __init__(self, contacts: list[UnreadContact], main_window: bool = True, send_success: bool = True) -> None:
        self.contacts = contacts
        self.main_window = main_window
        self.send_success = send_success
        self.opened: list[str] = []
        self.sent: list[tuple[str, str]] = []
        self.closed = 0

    def main_window_exists(self) -> bool:
        return self.main_window

    def unread_contacts(self) -> list[UnreadContact]:
        return self.contacts

    def open_chat(self, contact: UnreadContact) -> bool:
        self.opened.append(contact.name)
        return True

    def read_visible_chat(self, target_name: str) -> str:
        return f"{target_name}: 你還記得那個網站嗎？"

    def send_message(self, target_name: str, reply: str) -> bool:
        assert target_name in self.opened
        self.sent.append((target_name, reply))
        return self.send_success

    def close_chat(self, target_name: str) -> None:
        assert target_name in self.opened
        self.closed += 1


@dataclass
class FakeAi:
    reply: str = "我有點忘了，是哪個？"

    def generate_reply(self, **_kwargs) -> str:
        return self.reply


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
    assert [(item["role"], item["content"]) for item in repo.list_messages(target["id"])] == [
        ("scammer", "投資顧問✨: 你還記得那個網站嗎？"),
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


def test_stop_during_chat_read_prevents_ai_and_paste(repo):
    repo.create_target(target_payload("投資顧問"))
    calls = []
    controller = None

    class StopDuringReadLine(FakeLine):
        def read_visible_chat(self, target_name: str) -> str:
            controller.stop()
            return super().read_visible_chat(target_name)

    class RecordingAi(FakeAi):
        def generate_reply(self, **kwargs) -> str:
            calls.append(kwargs)
            return super().generate_reply(**kwargs)

    line = StopDuringReadLine([UnreadContact(index=1, name="投資顧問")])
    controller = MonitorController(repo, line, RecordingAi(), sleeper=lambda _seconds: None)
    controller.start(background=False)

    assert controller.run_cycle() is False
    assert calls == []
    assert line.sent == []


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
