from __future__ import annotations

from AppKit import NSApplication, NSButton, NSFontAttributeName, NSFontBoldTrait, NSStatusBar

from sweety_app.database import Database
from sweety_app.panel import (
    PanelBridge,
    PanelWindowController,
    _panel_button,
    _update_note_label,
    panel_update_copy,
    panel_update_downloads,
    status_text,
)
from sweety_app.repositories import Repository
from sweety_app.updates import UpdateState


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


def test_bridge_shares_update_snapshot_and_opens_only_available_platform(tmp_path):
    database = Database(tmp_path / "panel-update.sqlite3")
    database.migrate()
    repo = Repository(database)
    state = UpdateState()
    state.finish({
        "checked": True,
        "updateAvailable": True,
        "latestVersion": "1.1.0",
        "downloads": {
            "macos": "https://sweety.tw/Sweety.dmg",
            "windows": "http://example.com/Sweety.exe",
            "other": "https://example.com/other",
        },
    })
    opened = []
    bridge = PanelBridge(
        repo,
        FakeMonitor(),
        update_state=state,
        opener=opened.append,
        quit_callback=lambda: None,
    )

    assert bridge.snapshot()["update"]["latestVersion"] == "1.1.0"
    assert bridge.open_update("macos") is True
    assert bridge.open_update("windows") is False
    assert bridge.open_update("other") is False
    assert opened == ["https://sweety.tw/Sweety.dmg"]


def test_bridge_defaults_to_checked_no_update_snapshot(tmp_path):
    database = Database(tmp_path / "panel-default-update.sqlite3")
    database.migrate()
    repo = Repository(database)
    bridge = PanelBridge(repo, FakeMonitor(), quit_callback=lambda: None)

    assert bridge.snapshot()["update"] == {"checked": True, "updateAvailable": False}


def test_panel_update_copy_and_downloads_are_localized_and_omit_missing_platforms():
    update = {
        "checked": True,
        "updateAvailable": True,
        "latestVersion": "1.1.0",
        "downloads": {"macos": "https://sweety.tw/Sweety.dmg"},
    }

    assert panel_update_copy("zh-TW", update) == {
        "heading": "新版 1.1.0，立即下載",
        "note": "＊Mac OS 版安裝後請重新設定，輔助使用、螢幕與系統錄音以及自動化等三種權限",
        "emphasis": "螢幕與系統錄音以及自動化等三種權限",
        "windows": "Win 版",
        "macos": "Mac OS 版",
    }
    assert panel_update_copy("en", update) == {
        "heading": "Version 1.1.0 is ready to download",
        "note": "After installing the Mac OS version, configure Accessibility, Screen & System Audio Recording, and Automation permissions again.",
        "emphasis": "Screen & System Audio Recording, and Automation permissions",
        "windows": "Windows",
        "macos": "Mac OS",
    }
    assert panel_update_downloads(update) == [("macos", "https://sweety.tw/Sweety.dmg")]


def test_panel_update_downloads_are_ordered_and_require_an_available_update():
    downloads = {
        "macos": "https://sweety.tw/Sweety.dmg",
        "windows": "https://sweety.tw/Sweety.exe",
        "other": "https://example.com/other",
    }

    assert panel_update_downloads({"updateAvailable": True, "downloads": downloads}) == [
        ("windows", "https://sweety.tw/Sweety.exe"),
        ("macos", "https://sweety.tw/Sweety.dmg"),
    ]
    assert panel_update_downloads({"updateAvailable": False, "downloads": downloads}) == []


def test_native_update_note_boldly_emphasizes_the_permission_phrase():
    copy = panel_update_copy("zh-TW", {"latestVersion": "1.1.0"})
    attributed = _update_note_label(copy).attributedStringValue()
    emphasis_start = copy["note"].find(copy["emphasis"])

    font, _effective_range = attributed.attribute_atIndex_effectiveRange_(
        NSFontAttributeName,
        emphasis_start,
        None,
    )

    assert font.fontDescriptor().symbolicTraits() & NSFontBoldTrait


def test_native_panel_keeps_base_size_without_an_update_and_expands_only_once(tmp_path):
    NSApplication.sharedApplication()
    database = Database(tmp_path / "panel-layout.sqlite3")
    database.migrate()
    repo = Repository(database)
    state = UpdateState()
    bridge = PanelBridge(
        repo,
        FakeMonitor(),
        update_state=state,
        quit_callback=lambda: None,
    )
    controller = PanelWindowController.alloc().initWithBridge_locale_(bridge, "zh-TW")
    controller.build()

    try:
        assert tuple(controller.window.contentView().frame().size) == (420.0, 500.0)
        original_header_y = controller.logo_view.frame().origin.y
        state.finish({
            "checked": True,
            "updateAvailable": True,
            "latestVersion": "1.1.0",
            "downloads": {"macos": "https://sweety.tw/Sweety.dmg"},
        })

        controller.refresh_(None)
        first_frame = controller.window.frame()
        assert tuple(first_frame.size) == (420.0, 650.0)
        assert controller.logo_view.frame().origin.y == original_header_y + 150
        assert len(controller.update_views) == 1
        buttons = [view for view in controller.update_views[0].subviews() if isinstance(view, NSButton)]
        assert [str(button.identifier()) for button in buttons] == ["macos"]

        controller.refresh_(None)
        assert controller.window.frame() == first_frame
        assert len(controller.update_views) == 1
    finally:
        if controller.timer is not None:
            controller.timer.invalidate()
        if controller.status_item is not None:
            NSStatusBar.systemStatusBar().removeStatusItem_(controller.status_item)
        controller.window.setDelegate_(None)
        controller.window.close()
