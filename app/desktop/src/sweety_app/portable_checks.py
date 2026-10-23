"""Offline checks of the actual frozen Windows executable; no LINE login/send."""
from __future__ import annotations

import json
from pathlib import Path
import socket
import tempfile
import uuid


def self_check(output):
    import keyring
    import requests
    from . import bootstrap
    from .config import LOG_ENABLED, LOG_PATH
    from .okline_session import SessionVault, node_path, sdk_factory
    from .windows import run_window, single_instance

    report = {'ok': False, 'logging': LOG_ENABLED, 'node': node_path()}
    destination = Path(output)
    try:
        with tempfile.TemporaryDirectory(prefix='sweety-portable-check-') as directory:
            bootstrap.DATA_DIR = Path(directory)
            bootstrap.DATABASE_PATH = Path(directory) / 'sweety.sqlite3'
            bootstrap.LOG_PATH = Path(directory) / 'logs' / 'sweety.log'
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                bootstrap.API_PORT = sock.getsockname()[1]
            report['dataIsolated'] = True
            name = 'Local\\Sweety.Check.' + uuid.uuid4().hex
            with single_instance(name) as first:
                with single_instance(name) as second:
                    assert first and not second
            report['singleInstance'] = True

            vault = SessionVault(Path(directory) / 'sessions', uuid.uuid4().hex)
            try:
                vault.save({'test': '中文 session round trip'})
                assert vault.load() == {'test': '中文 session round trip'}
                assert b'round trip' not in vault.path.read_bytes()
                report['keyringBackend'] = type(keyring.get_keyring()).__module__
            finally:
                vault.clear()
                try:
                    keyring.delete_password('Sweety.OkLine', vault.owner)
                except keyring.errors.PasswordDeleteError:
                    pass

            api = sdk_factory()
            try:
                signature = api.transport.signer.sign('offline-self-check', '/offline', '{}')
                assert signature
                report['signatureLength'] = len(signature)
            finally:
                api.close()

            def ready(services, root):
                base = f'http://127.0.0.1:{bootstrap.API_PORT}'
                assert requests.get(base + '/api/health', timeout=5).json() == {'ok': True}
                page = requests.get(base + '/', timeout=5)
                assert page.status_code == 200 and '<html' in page.text.lower()
                import re
                scripts = re.findall(r'src="([^"]+\.js)"', page.text)
                assert scripts
                for script in scripts:
                    assert requests.get(base + '/' + script.lstrip('/'), timeout=5).status_code == 200
                assert requests.get(base + '/api/settings', timeout=5).status_code == 200
                assert requests.get(base + '/api/line/status', timeout=5).json()['status'] == 'disconnected'
                assert root.winfo_exists()
                report.update(gui=True, frontend=True, api=True)
                report['services'] = services

            run_window(factory=lambda: bootstrap.start_services(external=False),
                       on_ready=ready, open_browser=False)
            services = report.pop('services')
            assert not services.runtime.is_running
            report['shutdown'] = True
            report['logCreated'] = bootstrap.LOG_PATH.exists()
            assert report['logCreated'] == LOG_ENABLED
            report['ok'] = True
    except Exception as exc:
        report.pop('services', None)
        report['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
