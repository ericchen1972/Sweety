"""System-input ownership for macOS. Does not change LINE or speaker settings."""
from __future__ import annotations

import ctypes as C
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

BLACKHOLE_DOWNLOAD_URL = "https://existential.audio/blackhole/"


class BlackHoleRequired(RuntimeError):
    pass


@dataclass(frozen=True)
class AudioDevice:
    object_id: int
    uid: str
    name: str


class AudioBackend(Protocol):
    def input_devices(self) -> list[AudioDevice]: ...
    def default_input_uid(self) -> str: ...
    def set_default_input(self, uid: str) -> None: ...


class MicrophoneRoute:
    def __init__(self, audio: AudioBackend, recovery_path: Path):
        self.audio = audio
        self.recovery_path = recovery_path
        self._lease: dict[str, str] | None = None

    @property
    def active(self) -> bool:
        return self._lease is not None

    def recover(self) -> None:
        if self._lease is None and self.recovery_path.exists():
            payload = json.loads(self.recovery_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or not all(isinstance(payload.get(k), str) and payload[k] for k in ("original", "temporary")):
                raise RuntimeError("Invalid microphone recovery record")
            self._lease = {k: payload[k] for k in ("original", "temporary")}
        self.release()

    def acquire(self) -> None:
        if self.active:
            return
        self.recover()
        devices = [d for d in self.audio.input_devices() if d.name == "BlackHole 2ch" and "BlackHole2ch" in d.uid]
        if len(devices) != 1:
            raise BlackHoleRequired("BlackHole 2ch is required")
        original = self.audio.default_input_uid()
        lease = {"original": original, "temporary": devices[0].uid}
        self.recovery_path.parent.mkdir(parents=True, exist_ok=True)
        pending = self.recovery_path.with_suffix(".tmp")
        pending.write_text(json.dumps(lease), encoding="utf-8")
        pending.replace(self.recovery_path)
        self._lease = lease
        try:
            self.audio.set_default_input(lease["temporary"])
            if self.audio.default_input_uid() != lease["temporary"]:
                raise RuntimeError("System microphone switch was not retained")
        except Exception:
            self.release()
            raise

    def release(self) -> None:
        if self._lease is None:
            return
        lease = self._lease
        if self.audio.default_input_uid() == lease["temporary"]:
            self.audio.set_default_input(lease["original"])
            if self.audio.default_input_uid() != lease["original"]:
                raise RuntimeError("System microphone restoration was not retained")
        self.recovery_path.unlink(missing_ok=True)
        self._lease = None


class _Address(C.Structure):
    _fields_ = [("selector", C.c_uint32), ("scope", C.c_uint32), ("element", C.c_uint32)]


def _code(value: str) -> int:
    return int.from_bytes(value.encode("ascii"), "big")


class CoreAudioInput:
    def __init__(self):
        self.ca = C.CDLL("/System/Library/Frameworks/CoreAudio.framework/CoreAudio")
        self.cf = C.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        self.ca.AudioObjectGetPropertyDataSize.argtypes = [C.c_uint32, C.POINTER(_Address), C.c_uint32, C.c_void_p, C.POINTER(C.c_uint32)]
        self.ca.AudioObjectGetPropertyData.argtypes = [C.c_uint32, C.POINTER(_Address), C.c_uint32, C.c_void_p, C.POINTER(C.c_uint32), C.c_void_p]
        self.ca.AudioObjectSetPropertyData.argtypes = [C.c_uint32, C.POINTER(_Address), C.c_uint32, C.c_void_p, C.c_uint32, C.c_void_p]
        self.cf.CFStringGetCString.argtypes = [C.c_void_p, C.c_void_p, C.c_long, C.c_uint32]
        self.cf.CFStringGetCString.restype = C.c_bool
        self.cf.CFRelease.argtypes = [C.c_void_p]

    @staticmethod
    def _check(status: int) -> None:
        if status:
            raise RuntimeError(f"Core Audio error {status}")

    def _read(self, device: int, selector: str, scope: str = "glob") -> bytes:
        address = _Address(_code(selector), _code(scope), 0)
        size = C.c_uint32()
        self._check(self.ca.AudioObjectGetPropertyDataSize(device, C.byref(address), 0, None, C.byref(size)))
        data = C.create_string_buffer(size.value)
        self._check(self.ca.AudioObjectGetPropertyData(device, C.byref(address), 0, None, C.byref(size), data))
        return data.raw

    def _string(self, device: int, selector: str) -> str:
        pointer = C.c_void_p.from_buffer_copy(self._read(device, selector))
        if not pointer.value:
            raise RuntimeError("Missing audio device identity")
        try:
            data = C.create_string_buffer(4096)
            if not self.cf.CFStringGetCString(pointer, data, len(data), 0x08000100):
                raise RuntimeError("Unreadable audio device identity")
            return data.value.decode("utf-8")
        finally:
            self.cf.CFRelease(pointer)

    def input_devices(self) -> list[AudioDevice]:
        raw = self._read(1, "dev#")
        result = []
        for device in (C.c_uint32 * (len(raw) // 4)).from_buffer_copy(raw):
            try:
                if self._read(device, "stm#", "inpt"):
                    result.append(AudioDevice(int(device), self._string(device, "uid "), self._string(device, "lnam")))
            except RuntimeError:
                continue  # A hot-unplug can race device enumeration.
        return result

    def default_input_uid(self) -> str:
        device = C.c_uint32.from_buffer_copy(self._read(1, "dIn ")).value
        return self._string(device, "uid ")

    def set_default_input(self, uid: str) -> None:
        device = next((d for d in self.input_devices() if d.uid == uid), None)
        if device is None:
            raise RuntimeError("Requested microphone is no longer connected")
        address = _Address(_code("dIn "), _code("glob"), 0)
        value = C.c_uint32(device.object_id)
        self._check(self.ca.AudioObjectSetPropertyData(1, C.byref(address), 0, None, C.sizeof(value), C.byref(value)))
