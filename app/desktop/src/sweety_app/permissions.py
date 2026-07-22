from __future__ import annotations

import ctypes
import sys
from collections.abc import Callable
from dataclasses import dataclass


SYSTEM_EVENTS_BUNDLE_ID = "com.apple.systemevents"
LINE_BUNDLE_ID = "jp.naver.line.mac"


@dataclass(frozen=True)
class AutomationPermissionStatus:
    system_events: bool
    line: bool

    @property
    def ready(self) -> bool:
        return self.system_events and self.line

    @property
    def missing(self) -> tuple[str, ...]:
        missing = []
        if not self.system_events:
            missing.append("System Events")
        if not self.line:
            missing.append("LINE")
        return tuple(missing)


@dataclass(frozen=True)
class PermissionStatus:
    accessibility: bool
    screen_recording: bool
    automation: AutomationPermissionStatus

    @property
    def ready(self) -> bool:
        return self.accessibility and self.screen_recording and self.automation.ready

    @property
    def missing(self) -> tuple[str, ...]:
        missing = []
        if not self.accessibility:
            missing.append("Accessibility")
        if not self.screen_recording:
            missing.append("Screen Recording")
        missing.extend(self.automation.missing)
        return tuple(missing)


def _automation_script(bundle_id: str) -> str:
    if bundle_id == SYSTEM_EVENTS_BUNDLE_ID:
        return f'tell application id "{bundle_id}" to keystroke ""'
    return f'tell application id "{bundle_id}" to activate'


def _native_automation_probe(bundle_id: str, prompt: bool) -> bool:
    if prompt:
        from Foundation import NSAppleScript

        script = NSAppleScript.alloc().initWithSource_(_automation_script(bundle_id))
        result, _error = script.executeAndReturnError_(None)
        return result is not None

    class AEDesc(ctypes.Structure):
        _fields_ = [("descriptor_type", ctypes.c_uint32), ("data_handle", ctypes.c_void_p)]

    services = ctypes.CDLL("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
    services.AECreateDesc.argtypes = [
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_long,
        ctypes.POINTER(AEDesc),
    ]
    services.AECreateDesc.restype = ctypes.c_int32
    services.AEDeterminePermissionToAutomateTarget.argtypes = [
        ctypes.POINTER(AEDesc),
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_ubyte,
    ]
    services.AEDeterminePermissionToAutomateTarget.restype = ctypes.c_int32
    services.AEDisposeDesc.argtypes = [ctypes.POINTER(AEDesc)]

    bundle_data = bundle_id.encode("utf-8")
    bundle_buffer = ctypes.create_string_buffer(bundle_data)
    target = AEDesc()
    create_status = services.AECreateDesc(
        int.from_bytes(b"bund", "big"),
        bundle_buffer,
        len(bundle_data),
        ctypes.byref(target),
    )
    if create_status != 0:
        return False
    try:
        status = services.AEDeterminePermissionToAutomateTarget(
            ctypes.byref(target),
            int.from_bytes(b"****", "big"),
            int.from_bytes(b"****", "big"),
            0,
        )
        return status == 0
    finally:
        services.AEDisposeDesc(ctypes.byref(target))


def check_automation_permissions(
    *,
    prompt: bool = False,
    probe: Callable[[str, bool], bool] = _native_automation_probe,
) -> AutomationPermissionStatus:
    results = []
    for bundle_id in (SYSTEM_EVENTS_BUNDLE_ID, LINE_BUNDLE_ID):
        try:
            results.append(bool(probe(bundle_id, prompt)))
        except (ImportError, OSError, RuntimeError):
            results.append(False)
    return AutomationPermissionStatus(system_events=results[0], line=results[1])


def check_permissions(prompt: bool = True) -> PermissionStatus:
    if sys.platform != "darwin":
        return PermissionStatus(True, True, AutomationPermissionStatus(True, True))

    accessibility = False
    screen_recording = False
    try:
        from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt

        accessibility = bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: prompt}))
    except ImportError:
        pass

    try:
        from Quartz import CGPreflightScreenCaptureAccess, CGRequestScreenCaptureAccess

        screen_recording = bool(CGPreflightScreenCaptureAccess())
        if prompt and not screen_recording:
            screen_recording = bool(CGRequestScreenCaptureAccess())
    except (ImportError, AttributeError):
        screen_recording = False

    return PermissionStatus(accessibility, screen_recording, check_automation_permissions(prompt=prompt))
