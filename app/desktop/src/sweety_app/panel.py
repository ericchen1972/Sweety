from __future__ import annotations

from collections.abc import Callable
from typing import Any

import objc
from AppKit import (
    NSApplication,
    NSBackingStoreBuffered,
    NSButton,
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSImage,
    NSImageLeading,
    NSImageScaleProportionallyUpOrDown,
    NSImageView,
    NSLineBreakByWordWrapping,
    NSMakeRect,
    NSMenu,
    NSMenuItem,
    NSStatusBar,
    NSTextAlignmentCenter,
    NSTextField,
    NSVariableStatusItemLength,
    NSView,
    NSWorkspace,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskTitled,
)
from Foundation import NSMutableAttributedString, NSMakeRange, NSObject, NSTimer, NSURL

from .config import APP_VERSION, LOGO_PATH, MANAGEMENT_URL
from .repositories import Repository
from .updates import SUPPORTED_PLATFORMS, is_valid_https_url


STATUS_COPY = {
    "zh-TW": {
        "stopped": "已停止",
        "monitoring": "正在監控新訊息",
        "waiting": "等待新訊息",
        "processing": "正在處理",
        "permission_required": "需要 macOS 權限",
        "line_window_required": "請先開啟 LINE 主視窗",
        "target_required": "請先勾選至少一個對象",
        "error": "發生錯誤",
    },
    "en": {
        "stopped": "Stopped",
        "monitoring": "Monitoring for new messages",
        "waiting": "Waiting for new messages",
        "processing": "Processing",
        "permission_required": "macOS permissions required",
        "line_window_required": "Open the LINE main window first",
        "target_required": "Select at least one target first",
        "error": "Error",
    },
}


def status_text(locale: str, snapshot: dict[str, Any]) -> str:
    language = "zh-TW" if locale == "zh-TW" else "en"
    status = str(snapshot.get("status", "stopped"))
    text = STATUS_COPY[language].get(status, status)
    if snapshot.get("currentTarget"):
        text += f"：{snapshot['currentTarget']}" if language == "zh-TW" else f": {snapshot['currentTarget']}"
    if snapshot.get("message") and status not in {"permission_required", "line_window_required", "target_required"}:
        text += f" ({snapshot['message']})"
    return text


def panel_update_downloads(update: dict[str, Any]) -> list[tuple[str, str]]:
    if not update.get("updateAvailable"):
        return []
    downloads = update.get("downloads")
    if not isinstance(downloads, dict):
        return []
    return [
        (platform, url)
        for platform in SUPPORTED_PLATFORMS
        if is_valid_https_url(url := downloads.get(platform))
    ]


def panel_update_copy(locale: str, update: dict[str, Any]) -> dict[str, str]:
    version = str(update.get("latestVersion", ""))
    if locale == "zh-TW":
        return {
            "heading": f"新版 {version}，立即下載",
            "note": "＊Mac OS 版安裝後請重新設定，輔助使用、螢幕與系統錄音以及自動化等三種權限",
            "emphasis": "螢幕與系統錄音以及自動化等三種權限",
            "windows": "Win 版",
            "macos": "Mac OS 版",
        }
    return {
        "heading": f"Version {version} is ready to download",
        "note": "After installing the Mac OS version, configure Accessibility, Screen & System Audio Recording, and Automation permissions again.",
        "emphasis": "Screen & System Audio Recording, and Automation permissions",
        "windows": "Windows",
        "macos": "Mac OS",
    }


def _open_external_url(url: str) -> bool:
    return bool(NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(url)))


class PanelBridge:
    def __init__(
        self,
        repository: Repository,
        monitor: Any,
        *,
        update_state: Any | None = None,
        opener: Callable[[str], Any] = _open_external_url,
        quit_callback: Callable[[], None],
        on_changed: Callable[[], None] | None = None,
    ) -> None:
        self.repository = repository
        self.monitor = monitor
        self.update_state = update_state
        self.opener = opener
        self.quit_callback = quit_callback
        self.on_changed = on_changed or (lambda: None)

    def snapshot(self) -> dict[str, Any]:
        payload = self.monitor.snapshot()
        payload["selectedTargetCount"] = len(self.repository.list_monitor_targets())
        payload["version"] = APP_VERSION
        payload["update"] = (
            self.update_state.snapshot()
            if self.update_state is not None
            else {"checked": True, "updateAvailable": False}
        )
        return payload

    def open_update(self, platform: str) -> bool:
        if platform not in SUPPORTED_PLATFORMS:
            return False
        update = self.snapshot()["update"]
        downloads = dict(panel_update_downloads(update))
        url = downloads.get(platform)
        if url is None:
            return False
        self.opener(url)
        return True

    def start_monitor(self) -> bool:
        changed = bool(self.monitor.start())
        self.on_changed()
        return changed

    def stop_monitor(self) -> bool:
        changed = bool(self.monitor.stop())
        self.on_changed()
        return changed

    def open_management(self) -> None:
        self.opener(MANAGEMENT_URL)

    def quit_app(self) -> None:
        self.quit_callback()


def _label(text: str, frame: tuple[int, int, int, int], size: float, bold: bool = False) -> NSTextField:
    label = NSTextField.labelWithString_(text)
    label.setFrame_(NSMakeRect(*frame))
    label.setFont_(NSFont.boldSystemFontOfSize_(size) if bold else NSFont.systemFontOfSize_(size))
    return label


def _system_symbol(name: str, description: str) -> NSImage | None:
    return NSImage.imageWithSystemSymbolName_accessibilityDescription_(name, description)


def _update_note_label(copy: dict[str, str]) -> NSTextField:
    label = _label("", (16, 48, 340, 52), 11)
    attributed = NSMutableAttributedString.alloc().initWithString_(copy["note"])
    attributed.addAttribute_value_range_(
        NSFontAttributeName,
        NSFont.systemFontOfSize_(11),
        NSMakeRange(0, len(copy["note"])),
    )
    emphasis_start = copy["note"].find(copy["emphasis"])
    if emphasis_start >= 0:
        attributed.addAttribute_value_range_(
            NSFontAttributeName,
            NSFont.boldSystemFontOfSize_(11),
            NSMakeRange(emphasis_start, len(copy["emphasis"])),
        )
    label.setAttributedStringValue_(attributed)
    label.setLineBreakMode_(NSLineBreakByWordWrapping)
    label.setMaximumNumberOfLines_(3)
    return label


def _panel_button(
    title: str,
    target: Any,
    action: str,
    y: int,
    *,
    primary: bool = False,
    symbol_name: str,
) -> NSButton:
    button = NSButton.buttonWithTitle_target_action_(title, target, action)
    button.setFrame_(NSMakeRect(32, y, 356, 44))
    button.setBordered_(False)
    button.setWantsLayer_(True)
    button.layer().setCornerRadius_(6.0)
    button.layer().setBackgroundColor_(
        (NSColor.controlAccentColor() if primary else NSColor.tertiaryLabelColor().colorWithAlphaComponent_(0.22)).CGColor()
    )
    button.setContentTintColor_(NSColor.whiteColor() if primary else NSColor.labelColor())
    button.setFont_(NSFont.boldSystemFontOfSize_(14))
    button.setImage_(_system_symbol(symbol_name, title))
    button.setImagePosition_(NSImageLeading)
    button.setImageHugsTitle_(True)
    return button


class PanelWindowController(NSObject):
    def initWithBridge_locale_(self, bridge: PanelBridge, locale: str):
        self = objc.super(PanelWindowController, self).init()
        if self is None:
            return None
        self.bridge = bridge
        self.locale = "zh-TW" if locale == "zh-TW" else "en"
        self.window = None
        self.status_item = None
        self.timer = None
        self.update_views = []
        self.update_layout_applied = False
        return self

    def build(self) -> None:
        style = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskMiniaturizable
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 420, 500), style, NSBackingStoreBuffered, False
        )
        self.window.setTitle_("Sweety")
        self.window.setReleasedWhenClosed_(False)
        self.window.setDelegate_(self)
        self.window.center()
        content = self.window.contentView()

        logo = NSImage.alloc().initWithContentsOfFile_(str(LOGO_PATH))
        self.logo_view = NSImageView.alloc().initWithFrame_(NSMakeRect(24, 420, 48, 48))
        self.logo_view.setImage_(logo)
        self.logo_view.setImageScaling_(NSImageScaleProportionallyUpOrDown)
        content.addSubview_(self.logo_view)

        self.title_label = _label("Sweety", (84, 440, 210, 24), 19, True)
        content.addSubview_(self.title_label)
        self.subtitle_label = _label("Anti-scam companion", (84, 420, 220, 18), 12)
        content.addSubview_(self.subtitle_label)
        self.version_label = _label(f"v{APP_VERSION}", (328, 432, 66, 24), 11, True)
        self.version_label.setAlignment_(NSTextAlignmentCenter)
        content.addSubview_(self.version_label)

        selected_title = "已勾選對象" if self.locale == "zh-TW" else "Selected targets"
        content.addSubview_(_label(selected_title, (32, 344, 180, 20), 13))
        self.count_label = _label("0", (32, 292, 180, 52), 42, True)
        content.addSubview_(self.count_label)
        self.status_label = _label("", (32, 244, 356, 28), 13)
        content.addSubview_(self.status_label)

        self.toggle_button = _panel_button("", self, "toggleMonitor:", 174, primary=True, symbol_name="play.fill")
        self.toggle_button.setKeyEquivalent_("\r")
        content.addSubview_(self.toggle_button)

        manage_title = "開啟管理介面" if self.locale == "zh-TW" else "Open management"
        manage = _panel_button(manage_title, self, "openManagement:", 120, symbol_name="safari")
        content.addSubview_(manage)

        quit_title = "結束 App" if self.locale == "zh-TW" else "Quit App"
        quit_button = _panel_button(quit_title, self, "quitApp:", 56, symbol_name="power")
        content.addSubview_(quit_button)

        self._build_status_item(logo)
        self.refresh_(None)
        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0, self, "refresh:", None, True
        )

    def _build_status_item(self, logo: NSImage) -> None:
        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        status_button = self.status_item.button()
        logo.setSize_((20, 20))
        status_button.setImage_(logo)
        status_button.setToolTip_("Sweety")
        menu = NSMenu.alloc().init()
        show_title = "顯示 Sweety" if self.locale == "zh-TW" else "Show Sweety"
        show_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(show_title, "showWindow:", "")
        show_item.setTarget_(self)
        menu.addItem_(show_item)
        menu.addItem_(NSMenuItem.separatorItem())
        quit_title = "結束" if self.locale == "zh-TW" else "Quit"
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(quit_title, "quitApp:", "q")
        quit_item.setTarget_(self)
        menu.addItem_(quit_item)
        self.status_item.setMenu_(menu)

    def show(self) -> None:
        self.window.makeKeyAndOrderFront_(None)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    def _apply_update_layout(self, update: dict[str, Any]) -> None:
        downloads = panel_update_downloads(update)
        if self.update_layout_applied or not downloads:
            return
        self.update_layout_applied = True
        frame = self.window.frame()
        self.window.setFrame_display_(
            NSMakeRect(frame.origin.x, frame.origin.y - 150, 420, 650),
            True,
        )
        for view in (self.logo_view, self.title_label, self.subtitle_label, self.version_label):
            moved = view.frame()
            moved.origin.y += 150
            view.setFrame_(moved)

        card = NSView.alloc().initWithFrame_(NSMakeRect(24, 378, 372, 142))
        card.setWantsLayer_(True)
        card.layer().setCornerRadius_(10.0)
        card.layer().setBorderWidth_(1.0)
        card.layer().setBorderColor_(
            NSColor.controlAccentColor().colorWithAlphaComponent_(0.55).CGColor()
        )
        card.layer().setBackgroundColor_(NSColor.controlBackgroundColor().CGColor())
        copy = panel_update_copy(self.locale, update)
        card.addSubview_(_label(copy["heading"], (16, 105, 340, 22), 15, True))
        card.addSubview_(_update_note_label(copy))
        button_width = 164 if len(downloads) == 2 else 340
        for index, (platform, _url) in enumerate(downloads):
            button = NSButton.buttonWithTitle_target_action_(copy[platform], self, "openUpdate:")
            button.setIdentifier_(platform)
            button.setFrame_(NSMakeRect(16 + index * 176, 10, button_width, 32))
            card.addSubview_(button)
        self.window.contentView().addSubview_(card)
        self.update_views.append(card)

    @objc.IBAction
    def toggleMonitor_(self, _sender) -> None:
        if self.bridge.snapshot().get("enabled"):
            self.bridge.stop_monitor()
        else:
            self.bridge.start_monitor()
        self.refresh_(None)

    @objc.IBAction
    def openManagement_(self, _sender) -> None:
        self.bridge.open_management()

    @objc.IBAction
    def openUpdate_(self, sender) -> None:
        self.bridge.open_update(str(sender.identifier()))

    @objc.IBAction
    def quitApp_(self, _sender) -> None:
        self.bridge.quit_app()

    @objc.IBAction
    def showWindow_(self, _sender) -> None:
        self.show()

    def refresh_(self, _timer) -> None:
        snapshot = self.bridge.snapshot()
        self._apply_update_layout(snapshot["update"])
        enabled = bool(snapshot.get("enabled"))
        self.count_label.setStringValue_(str(snapshot.get("selectedTargetCount", 0)))
        self.status_label.setStringValue_(status_text(self.locale, snapshot))
        self.toggle_button.setTitle_(
            ("停止" if enabled else "開始") if self.locale == "zh-TW" else ("Stop" if enabled else "Start")
        )
        self.toggle_button.setImage_(
            _system_symbol("stop.fill" if enabled else "play.fill", self.toggle_button.title())
        )

    def windowShouldClose_(self, _sender) -> bool:
        self.window.orderOut_(None)
        return False
