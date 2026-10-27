import subprocess
import sys
from types import SimpleNamespace

import pytest

from sweety_app.background_processes import BackgroundSubprocess, background_options


def test_adapter_preserves_pipes_and_existing_flags(monkeypatch):
    import sweety_app.background_processes as background
    monkeypatch.setattr(background, 'background_options', lambda: {'creationflags': 0x08000000})
    calls = []
    module = SimpleNamespace(PIPE=-1, Popen=lambda *a, **kw: calls.append((a, kw)),
                             run=lambda *a, **kw: calls.append((a, kw)))
    adapter = BackgroundSubprocess(module)
    adapter.Popen(['node', 'bridge.js'], stdin=-1, stdout=-1, creationflags=0x200)
    adapter.run(['node', '--version'], capture_output=True)
    assert calls[0][1] == {'stdin': -1, 'stdout': -1, 'creationflags': 0x08000200}
    assert calls[1][1] == {'capture_output': True, 'creationflags': 0x08000000}
    assert adapter.PIPE == -1


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows process console')
def test_background_child_has_no_console():
    result = subprocess.run([sys.executable, '-c',
        'import ctypes; print(bool(ctypes.windll.kernel32.GetConsoleWindow()))'],
        capture_output=True, text=True, check=True, **background_options())
    assert result.stdout.strip() == 'False'


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows LINE helper')
def test_line_signing_clients_start_hidden_without_global_popen_patch(monkeypatch):
    from okline import hmac_signer
    from sweety_app.okline_session import sdk_factory
    original = subprocess.Popen
    flags = []

    def tracked(*args, **kwargs):
        flags.append(kwargs.get('creationflags', 0))
        return original(*args, **kwargs)

    monkeypatch.setattr(subprocess, 'Popen', tracked)
    for _ in range(2):
        api = sdk_factory()
        try:
            assert api.transport.signer.sign('offline-test', '/offline', '{}')
        finally:
            api.close()
    assert isinstance(hmac_signer.subprocess, BackgroundSubprocess)
    assert subprocess.Popen is tracked  # the SDK adapter did not patch other callers
    assert len(flags) >= 2
    assert all(flag & subprocess.CREATE_NO_WINDOW for flag in flags)
