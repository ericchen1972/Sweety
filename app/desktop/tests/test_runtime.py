from __future__ import annotations

import socket

import requests

from sweety_app.api import create_app
from sweety_app.database import Database
from sweety_app.runtime import ServerRuntime


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_runtime_starts_and_stops_uvicorn(tmp_path):
    port = free_port()
    app = create_app(Database(tmp_path / "runtime.sqlite3"))
    runtime = ServerRuntime(app, host="127.0.0.1", port=port)

    runtime.start(timeout=8)
    response = requests.get(f"http://127.0.0.1:{port}/api/health", timeout=2)
    runtime.stop(timeout=8)

    assert response.json() == {"ok": True}
    assert runtime.is_running is False
