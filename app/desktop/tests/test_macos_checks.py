import json
import pytest


def test_failed_check_stops_services_and_restores_paths(tmp_path, monkeypatch):
    from sweety_app import bootstrap
    from sweety_app.macos_checks import self_check
    original = (bootstrap.DATA_DIR, bootstrap.DATABASE_PATH, bootstrap.LOG_PATH, bootstrap.API_PORT)
    stopped = []
    class Runtime:
        is_running = False
    class Services:
        runtime = Runtime()
        def stop(self):
            stopped.append(True)
    def start(*, external):
        assert external is False
        assert bootstrap.DATA_DIR.parent == tmp_path
        return Services()
    monkeypatch.setattr(bootstrap, 'start_services', start)
    import requests
    def fail(*args, **kwargs):
        raise RuntimeError('health check failed')
    monkeypatch.setattr(requests, 'get', fail)
    report = tmp_path / 'report.json'
    with pytest.raises(RuntimeError, match='health check failed'):
        self_check(report)
    assert stopped == [True]
    assert original == (bootstrap.DATA_DIR, bootstrap.DATABASE_PATH, bootstrap.LOG_PATH, bootstrap.API_PORT)
    assert json.loads(report.read_text())['ok'] is False
    assert list(tmp_path.iterdir()) == [report]
