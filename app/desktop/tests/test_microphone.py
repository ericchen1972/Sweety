from dataclasses import dataclass
import pytest
from sweety_app.microphone import MicrophoneRoute, AudioDevice, BlackHoleRequired

class Audio:
    def __init__(self):
        self.current = 'mic'
        self.devices = [AudioDevice(1, 'mic', 'UA-22'), AudioDevice(2, 'BlackHole2ch_UID', 'BlackHole 2ch')]
        self.fail = None
    def input_devices(self): return self.devices
    def default_input_uid(self): return self.current
    def set_default_input(self, uid):
        if uid == self.fail: raise RuntimeError('device failed')
        self.current = uid

def test_start_stop_and_repeat_preserves_original(tmp_path):
    audio = Audio(); route = MicrophoneRoute(audio, tmp_path / 'route.json')
    route.acquire(); route.acquire()
    assert audio.current == 'BlackHole2ch_UID'
    route.release(); route.release()
    assert audio.current == 'mic'
    assert not (tmp_path / 'route.json').exists()

def test_missing_blackhole_never_changes_input(tmp_path):
    audio = Audio(); audio.devices = audio.devices[:1]
    route = MicrophoneRoute(audio, tmp_path / 'route.json')
    with pytest.raises(BlackHoleRequired): route.acquire()
    assert audio.current == 'mic'

def test_user_change_is_preserved(tmp_path):
    audio = Audio(); route = MicrophoneRoute(audio, tmp_path / 'route.json')
    route.acquire(); audio.current = 'other'; route.release()
    assert audio.current == 'other'

def test_failed_switch_rolls_back(tmp_path):
    audio = Audio(); audio.fail = 'BlackHole2ch_UID'
    route = MicrophoneRoute(audio, tmp_path / 'route.json')
    with pytest.raises(RuntimeError): route.acquire()
    assert audio.current == 'mic'
    assert not (tmp_path / 'route.json').exists()

def test_restore_failure_can_retry_after_relaunch(tmp_path):
    audio = Audio(); path = tmp_path / 'route.json'; route = MicrophoneRoute(audio, path)
    route.acquire(); audio.fail = 'mic'
    with pytest.raises(RuntimeError): route.release()
    assert path.exists()
    audio.fail = None
    MicrophoneRoute(audio, path).recover()
    assert audio.current == 'mic'
    assert not path.exists()

def test_recovery_does_not_overwrite_user_change(tmp_path):
    audio = Audio(); path = tmp_path / 'route.json'
    MicrophoneRoute(audio, path).acquire(); audio.current = 'other'
    MicrophoneRoute(audio, path).recover()
    assert audio.current == 'other'
    assert not path.exists()

def test_existing_blackhole_default_is_preserved(tmp_path):
    audio = Audio(); audio.current = 'BlackHole2ch_UID'
    route = MicrophoneRoute(audio, tmp_path / 'route.json')
    route.acquire(); route.release()
    assert audio.current == 'BlackHole2ch_UID'


def test_switch_that_raises_after_changing_input_is_restored(tmp_path):
    class PartialAudio(Audio):
        def set_default_input(self, uid):
            super().set_default_input(uid)
            if uid == 'BlackHole2ch_UID': raise RuntimeError('late failure')
    audio = PartialAudio(); path = tmp_path / 'route.json'
    with pytest.raises(RuntimeError): MicrophoneRoute(audio, path).acquire()
    assert audio.current == 'mic'
    assert not path.exists()


def test_silently_rejected_switch_is_not_success(tmp_path):
    class RejectAudio(Audio):
        def set_default_input(self, uid): pass
    audio = RejectAudio(); path = tmp_path / 'route.json'
    with pytest.raises(RuntimeError, match='not retained'): MicrophoneRoute(audio, path).acquire()
    assert audio.current == 'mic'
    assert not path.exists()
