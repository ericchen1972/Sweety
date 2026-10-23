from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest
import requests


SOURCE = Path(__file__).resolve().parents[1] / 'src'


def test_frozen_logging_uses_bundled_setting_without_build_shell(tmp_path):
    (tmp_path / 'runtime-config.json').write_text(json.dumps({'SWEETY_LOG_ENABLED': '1'}))
    env = dict(os.environ, PYTHONPATH=str(SOURCE))
    env.pop('SWEETY_LOG_ENABLED', None)
    result = subprocess.run([sys.executable, '-c',
        'import sys; sys.frozen=True; sys._MEIPASS=sys.argv[1]; '
        'from sweety_app.config import LOG_ENABLED; print(LOG_ENABLED)', str(tmp_path)],
        env=env, capture_output=True, text=True, check=True)
    assert result.stdout.strip() == 'True'


def test_environment_can_disable_bundled_logging(tmp_path):
    (tmp_path / 'runtime-config.json').write_text(json.dumps({'SWEETY_LOG_ENABLED': '1'}))
    result = subprocess.run([sys.executable, '-c',
        'import sys; sys.frozen=True; sys._MEIPASS=sys.argv[1]; '
        'from sweety_app.config import LOG_ENABLED; print(LOG_ENABLED)', str(tmp_path)],
        env=dict(os.environ, PYTHONPATH=str(SOURCE), SWEETY_LOG_ENABLED='0'),
        capture_output=True, text=True, check=True)
    assert result.stdout.strip() == 'False'


def test_portable_backend_serves_dashboard_and_stops_without_macos(tmp_path, monkeypatch):
    from sweety_app import bootstrap
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    dashboard = tmp_path / 'frontend'
    dashboard.mkdir()
    (dashboard / 'index.html').write_text('<html>Sweety portable test</html>')
    monkeypatch.setattr(bootstrap, 'DATABASE_PATH', tmp_path / 'sweety.sqlite3')
    monkeypatch.setattr(bootstrap, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(bootstrap, 'FRONTEND_DIST', dashboard)
    monkeypatch.setattr(bootstrap, 'API_PORT', port)
    monkeypatch.setattr(bootstrap, 'LOG_ENABLED', False)
    services = bootstrap.start_services(external=False)
    try:
        assert services.runtime.is_running
        base = f'http://127.0.0.1:{port}'
        assert requests.get(base + '/api/health', timeout=2).json() == {'ok': True}
        assert 'Sweety portable test' in requests.get(base, timeout=2).text
        assert requests.get(base + '/api/line/status', timeout=2).json()['status'] == 'disconnected'
        assert not services.monitor.snapshot()['enabled']
    finally:
        services.stop()
    assert not services.runtime.is_running


def test_shutdown_still_stops_api_when_monitor_cleanup_fails():
    from sweety_app.bootstrap import Services
    calls = []
    class Monitor:
        def stop(self):
            calls.append('monitor')
            raise RuntimeError('cleanup failed')
    class Line:
        def disconnect(self, clear):
            assert clear is False
            calls.append('line')
    class Runtime:
        def stop(self):
            calls.append('api')
    services = Services(None, Monitor(), Line(), Runtime(), None, 'en')
    with pytest.raises(RuntimeError, match='cleanup failed'):
        services.stop()
    assert calls == ['monitor', 'line', 'api']


def test_launcher_routes_windows_without_importing_macos(monkeypatch):
    import importlib.util
    import types
    spec = importlib.util.spec_from_file_location('portable_launcher', SOURCE.parent / 'launcher.py')
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    calls = []
    windows = types.ModuleType('sweety_app.windows')
    windows.main = lambda: calls.append('windows')
    monkeypatch.setitem(sys.modules, 'sweety_app.windows', windows)
    monkeypatch.setattr(sys, 'platform', 'win32')
    monkeypatch.setattr(sys, 'argv', ['Sweety.exe'])
    launcher.main()
    assert calls == ['windows']


def test_service_shutdown_releases_diagnostic_file(tmp_path):
    from sweety_app.bootstrap import Services
    from sweety_app.diagnostics import configure_diagnostics
    from types import SimpleNamespace
    logger = configure_diagnostics(tmp_path / 'sweety.log', enabled=True)
    services = Services(None, SimpleNamespace(stop=lambda: None),
        SimpleNamespace(disconnect=lambda **kw: None), SimpleNamespace(stop=lambda: None), None, 'en')
    services.stop()
    assert not any(getattr(handler, '_sweety_diagnostics', False) for handler in logger.handlers)


def test_frozen_config_supports_shallow_extraction_path():
    # A drive-root extraction has fewer parents than the source checkout.
    code = (SOURCE / 'sweety_app/config.py').read_text()
    import types
    fake_sys = types.ModuleType('sys')
    fake_sys.frozen = True
    fake_sys._MEIPASS = '/Sweety/_internal'
    fake_sys.platform = 'win32'
    import builtins
    real_import = builtins.__import__
    def frozen_import(name, *args, **kwargs):
        return fake_sys if name == 'sys' else real_import(name, *args, **kwargs)
    namespace = {'__file__': '/Sweety/_internal/sweety_app/config.py',
        '__builtins__': dict(vars(builtins), __import__=frozen_import)}
    exec(compile(code, namespace['__file__'], 'exec'), namespace)
    assert namespace['RESOURCE_DIR'] == Path('/Sweety/_internal')
