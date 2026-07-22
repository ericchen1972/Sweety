from __future__ import annotations

import threading
import time
from typing import Any

import requests
import uvicorn


class ServerRuntime:
    def __init__(self, app: Any, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.server = uvicorn.Server(
            uvicorn.Config(app, host=host, port=port, log_level="warning", access_log=False)
        )
        self.thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return bool(self.thread and self.thread.is_alive() and self.server.started)

    def start(self, timeout: float = 15) -> None:
        if self.is_running:
            return
        self.server.should_exit = False
        self.thread = threading.Thread(target=self.server.run, name="SweetyLocalApi", daemon=True)
        self.thread.start()
        deadline = time.monotonic() + timeout
        health_url = f"http://{self.host}:{self.port}/api/health"
        while time.monotonic() < deadline:
            if self.thread is not None and not self.thread.is_alive():
                break
            try:
                response = requests.get(health_url, timeout=0.3)
                if response.ok:
                    return
            except requests.RequestException:
                pass
            time.sleep(0.1)
        self.stop()
        raise RuntimeError(f"Sweety API did not start at {health_url}")

    def stop(self, timeout: float = 10) -> None:
        self.server.should_exit = True
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=timeout)
        self.thread = None
