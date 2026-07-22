from __future__ import annotations

import threading
import time
from typing import Any, Callable

import requests

from .config import APP_VERSION
from .repositories import Repository


class MetricsReporter:
    def __init__(
        self,
        repository: Repository,
        url: str,
        token: str,
        *,
        session: Any = requests,
        thread_factory: Callable[..., threading.Thread] = threading.Thread,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.repository = repository
        self.url = url.strip()
        self.token = token.strip()
        self.session = session
        self.thread_factory = thread_factory
        self.clock = clock
        self._report_lock = threading.Lock()

    @property
    def configured(self) -> bool:
        return bool(self.url and self.token)

    def report(self) -> bool:
        if not self.configured:
            return False
        with self._report_lock:
            try:
                proposal = self._proposed_total_hours()
                response = self.session.post(
                    self.url,
                    json={
                        "installationId": self.repository.get_or_create_installation_id(),
                        "totalHours": proposal,
                    },
                    headers={
                        "X-Sweety-App": "desktop",
                        "X-Sweety-App-Token": self.token,
                        "User-Agent": f"SweetyApp/{APP_VERSION}",
                    },
                    timeout=5,
                )
                if response.status_code != 204:
                    return False
                self.repository.save_metrics_report_acceptance(proposal, int(self.clock()))
                return True
            except Exception:
                return False

    def _proposed_total_hours(self) -> int:
        local_total = max(0, int(self.repository.whole_duration_hours()))
        state = self.repository.get_metrics_report_state()
        if state is None:
            return min(local_total, 24)
        elapsed_whole_hours = max(0, int(self.clock()) - state["registered_at"]) // 3600
        ceiling = state["baseline_hours"] + elapsed_whole_hours + 2
        return max(state["accepted_hours"], min(local_total, ceiling))

    def report_async(self) -> None:
        if not self.configured:
            return
        try:
            worker = self.thread_factory(
                target=self.report,
                name="SweetyMetricsReporter",
                daemon=True,
            )
            worker.start()
        except Exception:
            return


def start_metrics_reporting(
    repository: Repository,
    url: str,
    token: str,
    *,
    session: Any = requests,
    thread_factory: Callable[..., threading.Thread] = threading.Thread,
    clock: Callable[[], float] = time.time,
) -> MetricsReporter:
    reporter = MetricsReporter(
        repository,
        url,
        token,
        session=session,
        thread_factory=thread_factory,
        clock=clock,
    )
    reporter.report_async()
    return reporter
