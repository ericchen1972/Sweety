from __future__ import annotations

from sweety_app.database import Database
from sweety_app.panel import PanelBridge, _panel_button, status_text
from sweety_app.repositories import Repository


class FakeMonitor:
    def __init__(self) -> None:
        self.enabled = False

    def start(self) -> bool:
        changed = not self.enabled
        self.enabled = True
        return changed

    def stop(self) -> bool:
        changed = self.enabled
        self.enabled = False
        return changed

    def snapshot(self):
        return {"enabled": self.enabled, "testMode": False, "status": "monitoring" if self.enabled else "stopped", "message": "", "currentTarget": None, "selectedTargetCount": 0}


def test_bridge_reports_count_and_controls_monitor(tmp_path):
    database = Database(tmp_path / "panel.sqlite3")
    database.migrate()
    repo = Repository(database)
    repo.create_target({
        "name": "A", "age_group": "20-35", "gender": "female",
        "persona_id": "cautious-accounting-assistant", "persona_source": "base",
        "weapon_id": "one-step-at-a-time", "weapon_source": "base", "reply_enabled": True,
    })
    monitor = FakeMonitor()
    opened = []
    changed = []
    bridge = PanelBridge(repo, monitor, opener=opened.append, quit_callback=lambda: None, on_changed=lambda: changed.append(True))

    assert bridge.snapshot()["selectedTargetCount"] == 1
    assert bridge.start_monitor() is True
    assert bridge.snapshot()["enabled"] is True
    assert bridge.stop_monitor() is True
    bridge.open_management()
    assert opened == ["http://127.0.0.1:8891/"]
    assert len(changed) == 2


def test_status_text_is_localized():
    assert status_text("zh-TW", {"status": "target_required"}) == "請先勾選至少一個對象"
    assert status_text("en", {"status": "line_window_required"}) == "Open the LINE main window first"


def test_panel_button_uses_requested_system_symbol():
    button = _panel_button("開始", None, "", 174, primary=True, symbol_name="play.fill")

    assert button.image() is not None
    assert button.image().accessibilityDescription() == "開始"
    assert button.imageHugsTitle() is True
