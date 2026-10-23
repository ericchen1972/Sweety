from __future__ import annotations

from AppKit import NSApplication, NSColor, NSCalibratedRGBColorSpace, NSButton, NSFontAttributeName, NSFontBoldTrait, NSStatusBar

from sweety_app.database import Database
from sweety_app.panel import (
    PanelBridge,
    PanelWindowController,
    _panel_button,
    _update_note_label,
    ai_timeout_alert_copy,
    panel_ui_copy,
    permission_alert_copy,
    panel_update_copy,
    panel_update_downloads,
    status_text,
)
from sweety_app.repositories import Repository
from sweety_app.updates import UpdateState


class FakeMonitor:
    def __init__(self) -> None:
        self.enabled = False
        self.ai_timeout_alert = False

    def start(self) -> bool:
        changed = not self.enabled
        self.enabled = True
        return changed

    def stop(self) -> bool:
        changed = self.enabled
        self.enabled = False
        return changed

    def snapshot(self):
        return {
            "enabled": self.enabled,
            "testMode": False,
            "status": "monitoring" if self.enabled else "stopped",
            "message": "",
            "currentTarget": None,
            "aiTimeoutAlert": self.ai_timeout_alert,
            "selectedTargetCount": 0,
        }


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

    assert bridge.snapshot()["selectedTargetCount"] == 0
    assert bridge.start_monitor() is True
    assert bridge.snapshot()["enabled"] is True
    assert bridge.stop_monitor() is True
    bridge.open_management()
    assert opened == ["http://127.0.0.1:8891/"]
    assert len(changed) == 2


def test_status_text_is_localized():
    assert status_text("zh-TW", {"status": "target_required"}) == "請先勾選至少一個對象"
    assert status_text("en", {"status": "line_window_required"}) == "Log in to LINE in management first"
    assert status_text("ja", {"status": "target_required"}) == "対象を1人以上選択してください"
    assert status_text("ja", {"status": "processing", "currentTarget": "Fraud1"}) == "処理中: Fraud1"


def test_ai_timeout_alert_copy_is_localized():
    assert ai_timeout_alert_copy("zh-TW") == "AI 目前沒有回應，請切換 AI 模型或稍後再試。"
    assert ai_timeout_alert_copy("en") == "AI is not responding. Switch AI models or try again later."
    assert ai_timeout_alert_copy("unsupported") == "AI is not responding. Switch AI models or try again later."
    assert ai_timeout_alert_copy("ja") == "AIが応答していません。AIモデルを切り替えるか、しばらくしてから再試行してください。"


def test_panel_subtitle_is_fixed_english_across_locales():
    for locale in ("zh-TW", "en", "ja", "unsupported"):
        assert panel_ui_copy(locale)["subtitle"] == "Scam Insecticide"


def test_panel_and_permission_copy_are_localized_in_japanese():
    copy = panel_ui_copy("ja")
    assert copy["subtitle"] == "Scam Insecticide"
    assert copy["selected_targets"] == "選択中の対象"
    assert copy["start"] == "開始"
    assert copy["stop"] == "停止"
    assert copy["open_management"] == "管理画面を開く"
    assert copy["quit_app"] == "Appを終了"

    alert = permission_alert_copy("ja", ["Accessibility", "Screen Recording", "LINE"])
    assert alert["title"] == "SweetyにはmacOSの権限が必要です"
    assert "アクセシビリティ" in alert["message"]
    assert "画面収録" in alert["message"]
    assert "LINEオートメーション" in alert["message"]


def test_bridge_preserves_monitor_timeout_alert_snapshot(tmp_path):
    database = Database(tmp_path / "panel-timeout.sqlite3")
    database.migrate()
    repo = Repository(database)
    monitor = FakeMonitor()
    monitor.ai_timeout_alert = True
    bridge = PanelBridge(repo, monitor, quit_callback=lambda: None)

    assert bridge.snapshot()["aiTimeoutAlert"] is True


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
        "note": "文字功能只需登入 LINE，不需要桌面操作權限。",
        "emphasis": "不需要桌面操作權限",
        "windows": "Win 版",
        "macos": "Mac OS 版",
    }
    assert panel_update_copy("en", update) == {
        "heading": "Version 1.1.0 is ready to download",
        "note": "Text features only require LINE sign-in. No desktop control permissions needed.",
        "emphasis": "No desktop control permissions needed",
        "windows": "Windows",
        "macos": "Mac OS",
    }
    assert panel_update_copy("ja", update) == {
        "heading": "バージョン 1.1.0 をダウンロードできます",
        "note": "文字機能はLINEログインのみで利用できます。",
        "emphasis": "LINEログイン",
        "windows": "Windows版",
        "macos": "Mac OS版",
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


def test_native_panel_uses_square_background_and_preserves_controls_with_update(tmp_path):
    NSApplication.sharedApplication()
    database = Database(tmp_path / "panel-layout.sqlite3")
    database.migrate()
    repo = Repository(database)
    state = UpdateState()
    monitor = FakeMonitor()
    bridge = PanelBridge(
        repo,
        monitor,
        update_state=state,
        quit_callback=lambda: None,
    )
    controller = PanelWindowController.alloc().initWithBridge_locale_(bridge, "zh-TW")
    controller.build()

    try:
        assert tuple(controller.window.frame().size) == (500.0, 500.0)
        assert controller.window.titlebarAppearsTransparent() is True
        assert tuple(controller.background_view.frame().size) == (500.0, 500.0)
        assert controller.background_view.image() is not None
        controls = [view for view in controller.window.contentView().subviews() if isinstance(view, NSButton)]
        assert len(controls) == 3
        assert {view.frame().origin.y for view in controls} == {28.0}
        assert [view.frame().origin.x for view in controls] == [32.0, 180.0, 328.0]
        assert controller.status_label.frame().size.width == 436
        assert controller.ai_timeout_alert.isHidden() is True
        stopped_color = NSColor.colorWithCGColor_(controller.toggle_button.layer().backgroundColor())
        monitor.enabled = True
        controller.refresh_(None)
        running_color = NSColor.colorWithCGColor_(controller.toggle_button.layer().backgroundColor())
        running_rgb = running_color.colorUsingColorSpaceName_(NSCalibratedRGBColorSpace)
        assert running_rgb.redComponent() > running_rgb.blueComponent()
        assert not running_color.isEqual_(stopped_color)
        assert controller.toggle_button.title() == "停止"
        monitor.enabled = False
        controller.refresh_(None)
        restored = NSColor.colorWithCGColor_(controller.toggle_button.layer().backgroundColor()).colorUsingColorSpaceName_(NSCalibratedRGBColorSpace)
        initial = stopped_color.colorUsingColorSpaceName_(NSCalibratedRGBColorSpace)
        assert restored.getRed_green_blue_alpha_(None,None,None,None) == initial.getRed_green_blue_alpha_(None,None,None,None)
        monitor.ai_timeout_alert = True
        controller.refresh_(None)
        assert controller.ai_timeout_alert.isHidden() is False
        monitor.ai_timeout_alert = False
        controller.refresh_(None)
        assert controller.ai_timeout_alert.isHidden() is True
        original_header_y = controller.logo_view.frame().origin.y
        state.finish({
            "checked": True,
            "updateAvailable": True,
            "latestVersion": "1.1.0",
            "downloads": {"macos": "https://sweety.tw/Sweety.dmg"},
        })

        controller.refresh_(None)
        first_frame = controller.window.frame()
        assert tuple(first_frame.size) == (500.0, 500.0)
        assert controller.logo_view.frame().origin.y == original_header_y
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


def test_text_panel_has_no_audio_controls():
    assert not hasattr(PanelBridge, 'open_blackhole_download')
    assert not hasattr(PanelWindowController, '_show_microphone_alert')
