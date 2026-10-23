from __future__ import annotations

import locale as system_locale
import logging
import signal

import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyRegular,
    NSImage,
)
from Foundation import NSObject

from .bootstrap import start_services
from .config import LOGO_PATH, preferred_locale
from .diagnostics import log_event
from .monitor import MonitorController
from .panel import PanelBridge, PanelWindowController
from .repositories import Repository
from .runtime import ServerRuntime
from .updates import UpdateState


def detected_locale() -> str:
    return preferred_locale(system_locale.getlocale()[0])


class SweetyAppDelegate(NSObject):
    def initWithComponents_locale_updateState_(
        self,
        components: tuple[Repository, MonitorController, ServerRuntime],
        locale: str,
        update_state: UpdateState,
    ):
        self = objc.super(SweetyAppDelegate, self).init()
        if self is None:
            return None
        self.repository, self.monitor, self.runtime = components
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
            update_state=self.update_state,
            quit_callback=lambda: application.terminate_(None),
        )
        self.panel = PanelWindowController.alloc().initWithBridge_locale_(bridge, self.locale)
        self.panel.build()
        self.panel.show()
    def applicationShouldTerminateAfterLastWindowClosed_(self, _application) -> bool:
        return False

    def applicationWillTerminate_(self, _notification) -> None:
        log_event(logging.getLogger("sweety.app"), "app_stopping")
        self.monitor.stop()
        self.monitor.line.disconnect(clear=False)
        self.runtime.stop()


def main() -> None:
    application = NSApplication.sharedApplication()
    application.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    locale = detected_locale()

    services = start_services()
    repository, monitor, runtime = services.repository, services.monitor, services.runtime
    update_state = services.update_state

    delegate = SweetyAppDelegate.alloc().initWithComponents_locale_updateState_(
        (repository, monitor, runtime), locale, update_state
    )
    application.setDelegate_(delegate)
    signal.signal(signal.SIGINT, lambda *_args: application.terminate_(None))
    signal.signal(signal.SIGTERM, lambda *_args: application.terminate_(None))
    try:
        application.run()
    finally:
        services.stop()


if __name__ == "__main__":
    main()
