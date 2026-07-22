from __future__ import annotations

import locale as system_locale
import signal
import threading

import objc
from AppKit import (
    NSAlert,
    NSAlertStyleWarning,
    NSApplication,
    NSApplicationActivationPolicyRegular,
    NSImage,
)
from Foundation import NSObject

from .ai import AiClient
from .about import AboutContentClient
from .api import create_app
from .config import ABOUT_SWEETY_URL, API_HOST, API_PORT, APP_VERSION, BUNDLED_AGNES_KEY, CACHE_DIR, DATABASE_PATH, FRONTEND_DIST, LOGO_PATH, REGION_LOOKUP_URL, REMOTE_CATALOG_URL, REMOTE_METRICS_URL, REMOTE_UPDATE_URL, SWEETY_METRICS_APP_TOKEN, preferred_locale
from .database import Database
from .line_mac import LineMacAdapter
from .monitor import MonitorController
from .metrics_reporter import start_metrics_reporting
from .panel import PanelBridge, PanelWindowController
from .permissions import PermissionStatus, check_permissions
from .remote_catalog import sync_remote_catalog
from .region_access import check_region_access
from .repositories import Repository
from .runtime import ServerRuntime
from .updates import UpdateState, check_remote_update


def detected_locale() -> str:
    return preferred_locale(system_locale.getlocale()[0])


class SweetyAppDelegate(NSObject):
    def initWithComponents_permissionStatus_locale_updateState_(
        self,
        components: tuple[Repository, MonitorController, ServerRuntime],
        permission_status: PermissionStatus,
        locale: str,
        update_state: UpdateState,
    ):
        self = objc.super(SweetyAppDelegate, self).init()
        if self is None:
            return None
        self.repository, self.monitor, self.runtime = components
        self.permission_status = permission_status
        self.locale = locale
        self.update_state = update_state
        self.panel = None
        return self

    def applicationDidFinishLaunching_(self, _notification) -> None:
        application = NSApplication.sharedApplication()
        application.setApplicationIconImage_(NSImage.alloc().initWithContentsOfFile_(str(LOGO_PATH)))
        bridge = PanelBridge(
            self.repository,
            self.monitor,
            quit_callback=lambda: application.terminate_(None),
        )
        self.panel = PanelWindowController.alloc().initWithBridge_locale_(bridge, self.locale)
        self.panel.build()
        self.panel.show()
        if not self.permission_status.ready:
            permission_names = {
                "Accessibility": "輔助使用",
                "Screen Recording": "螢幕錄製",
                "System Events": "System Events 自動化",
                "LINE": "LINE 自動化",
            }
            missing = ", ".join(
                permission_names.get(name, name) if self.locale == "zh-TW" else name
                for name in self.permission_status.missing
            )
            alert = NSAlert.alloc().init()
            alert.setAlertStyle_(NSAlertStyleWarning)
            alert.setMessageText_("Sweety 需要 macOS 權限" if self.locale == "zh-TW" else "Sweety needs macOS permissions")
            alert.setInformativeText_(
                f"尚未允許：{missing}。請完成授權，然後重新啟動 Sweety。"
                if self.locale == "zh-TW"
                else f"Not yet allowed: {missing}. Grant access, then restart Sweety."
            )
            alert.runModal()

    def applicationShouldTerminateAfterLastWindowClosed_(self, _application) -> bool:
        return False

    def applicationWillTerminate_(self, _notification) -> None:
        self.monitor.stop()
        self.runtime.stop()


def main() -> None:
    application = NSApplication.sharedApplication()
    application.setActivationPolicy_(NSApplicationActivationPolicyRegular)

    database = Database(DATABASE_PATH)
    database.migrate()
    repository = Repository(database)
    update_state = UpdateState()
    threading.Thread(
        target=check_remote_update,
        args=(update_state, APP_VERSION, REMOTE_UPDATE_URL),
        daemon=True,
    ).start()
    region_access = check_region_access(url=REGION_LOOKUP_URL)
    threading.Thread(
        target=sync_remote_catalog,
        args=(repository, REMOTE_CATALOG_URL),
        daemon=True,
    ).start()
    metrics_reporter = start_metrics_reporting(
        repository,
        REMOTE_METRICS_URL,
        SWEETY_METRICS_APP_TOKEN,
    )
    permission_status = check_permissions(prompt=True)
    line = LineMacAdapter(CACHE_DIR)
    ai = AiClient(agnes_key=BUNDLED_AGNES_KEY, repository=repository)
    monitor = MonitorController(
        repository,
        line,
        ai,
        automation_allowed=permission_status.ready,
        region_blocked=region_access.blocked,
        on_exchange_committed=metrics_reporter.report_async,
    )
    api = create_app(
        database,
        monitor=monitor,
        frontend_dist=FRONTEND_DIST,
        persona_validator=ai,
        about_loader=AboutContentClient(ABOUT_SWEETY_URL),
        update_state=update_state,
    )
    runtime = ServerRuntime(api, API_HOST, API_PORT)
    runtime.start()

    delegate = SweetyAppDelegate.alloc().initWithComponents_permissionStatus_locale_updateState_(
        (repository, monitor, runtime), permission_status, detected_locale(), update_state
    )
    application.setDelegate_(delegate)
    signal.signal(signal.SIGINT, lambda *_args: application.terminate_(None))
    signal.signal(signal.SIGTERM, lambda *_args: application.terminate_(None))
    application.run()


if __name__ == "__main__":
    main()
