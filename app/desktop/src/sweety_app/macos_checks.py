"""Offline frozen-macOS acceptance probe, isolated from the user's data."""
from __future__ import annotations

import json
from pathlib import Path
import re
import socket
import tempfile
import traceback


def self_check(output):
    import requests
    from . import bootstrap
    from .config import LOG_ENABLED
    from .okline_session import node_path, sdk_factory

    destination = Path(output).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    report = {"ok": False, "logging": LOG_ENABLED, "node": node_path()}
    original = (bootstrap.DATA_DIR, bootstrap.DATABASE_PATH, bootstrap.LOG_PATH, bootstrap.API_PORT)
    services = None
    try:
        with tempfile.TemporaryDirectory(prefix="sweety-macos-check-", dir=destination.parent) as directory:
            bootstrap.DATA_DIR = Path(directory)
            bootstrap.DATABASE_PATH = Path(directory) / "sweety.sqlite3"
            bootstrap.LOG_PATH = Path(directory) / "logs" / "sweety.log"
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                bootstrap.API_PORT = sock.getsockname()[1]
            report["dataIsolated"] = True
            try:
                services = bootstrap.start_services(external=False)
                base = f"http://127.0.0.1:{bootstrap.API_PORT}"
                health = requests.get(base + "/api/health", timeout=5)
                assert health.status_code == 200 and health.json() == {"ok": True}, "health"
                report["health"] = True
                page = requests.get(base + "/", timeout=5)
                assert page.status_code == 200 and "<html" in page.text.lower(), "frontend HTML"
                scripts = re.findall(r'src="([^" ]+\.js)"', page.text)
                assert scripts, "frontend JavaScript references"
                for script in scripts:
                    assert script.startswith("/") and not script.startswith("//"), "non-local frontend script"
                    response = requests.get(base + script, timeout=5)
                    assert response.status_code == 200 and response.content, script
                    assert "javascript" in response.headers.get("content-type", ""), script
                report["frontendScripts"] = scripts
                state = requests.get(base + "/api/state", timeout=5)
                assert state.status_code == 200 and isinstance(state.json(), dict), "state"
                report["state"] = True
                status = requests.get(base + "/api/line/status", timeout=5)
                assert status.status_code == 200 and status.json()["status"] == "disconnected", "LINE status"
                report["lineStatus"] = "disconnected"
                api = sdk_factory()
                try:
                    signature = api.transport.signer.sign("offline-self-check", "/offline", "{}")
                    assert signature, "offline signature"
                    report["signatureLength"] = len(signature)
                finally:
                    api.close()
                report["logCreated"] = bootstrap.LOG_PATH.exists()
                assert report["logCreated"] == LOG_ENABLED, "diagnostic log switch"
            finally:
                if services is not None:
                    services.stop()
                    report["shutdown"] = not services.runtime.is_running
                    assert report["shutdown"], "services still running"
            report["ok"] = True
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        report["traceback"] = traceback.format_exc()
        raise
    finally:
        bootstrap.DATA_DIR, bootstrap.DATABASE_PATH, bootstrap.LOG_PATH, bootstrap.API_PORT = original
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
