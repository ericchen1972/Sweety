"""Shared service composition; desktop hosts own the UI and process lifetime."""
from __future__ import annotations

from dataclasses import dataclass
import locale as system_locale
import logging
import threading

from .ai import AiClient
from .about import AboutContentClient
from .api import create_app
from .config import API_HOST, API_PORT, APP_VERSION, BUNDLED_AGNES_KEY, CACHE_DIR, DATABASE_PATH, DATA_DIR, FRONTEND_DIST, LOG_ENABLED, LOGO_PATH, LOG_PATH, REGION_LOOKUP_URL, REMOTE_CATALOG_URL, REMOTE_METRICS_URL, REMOTE_UPDATE_URL, SWEETY_METRICS_APP_TOKEN, about_url_for_locale, preferred_locale
from .database import Database
from .diagnostics import configure_diagnostics, log_event
from .okline_store import LineStore
from .okline_service import LineService
from .okline_session import SessionVault
from .monitor import MonitorController
from .metrics_reporter import start_metrics_reporting
from .remote_catalog import sync_remote_catalog
from .region_access import check_region_access
from .repositories import Repository
from .runtime import ServerRuntime
from .updates import UpdateState, check_remote_update

@dataclass
class Services:
    repository: Repository
    monitor: MonitorController
    line: LineService
    runtime: ServerRuntime
    update_state: UpdateState
    locale: str

    def stop(self) -> None:
        log_event(logging.getLogger("sweety.app"), "app_stopping")
        try:
            self.monitor.stop()
        finally:
            try:
                self.line.disconnect(clear=False)
            finally:
                try:
                    self.runtime.stop()
                finally:
                    configure_diagnostics(LOG_PATH, enabled=False)


def start_services(*, external: bool = True) -> Services:
    configure_diagnostics(LOG_PATH, enabled=LOG_ENABLED)
    log_event(logging.getLogger("sweety.app"), "app_started", version=APP_VERSION)
    locale = preferred_locale(system_locale.getlocale()[0])
    database = Database(DATABASE_PATH)
    database.migrate()
    repository = Repository(database)
    update_state = UpdateState()
    region_blocked = False
    if external:
        threading.Thread(target=check_remote_update,
            args=(update_state, APP_VERSION, REMOTE_UPDATE_URL), daemon=True).start()
        region_blocked = check_region_access(url=REGION_LOOKUP_URL).blocked
        threading.Thread(target=sync_remote_catalog,
            args=(repository, REMOTE_CATALOG_URL), daemon=True).start()
    metrics_reporter = start_metrics_reporting(
        repository, REMOTE_METRICS_URL if external else "", SWEETY_METRICS_APP_TOKEN)
    store = LineStore(repository)
    line = LineService(repository, store, vault=SessionVault(DATA_DIR / "line-sessions", "local"))
    ai = AiClient(agnes_key=BUNDLED_AGNES_KEY, repository=repository)
    monitor = MonitorController(repository, line, ai, region_blocked=region_blocked,
        on_exchange_committed=metrics_reporter.report_async)
    api = create_app(database, monitor=monitor, line_service=line,
        frontend_dist=FRONTEND_DIST, persona_validator=ai,
        about_loader=AboutContentClient(about_url_for_locale(locale)), update_state=update_state)
    runtime = ServerRuntime(api, API_HOST, API_PORT)
    services = Services(repository, monitor, line, runtime, update_state, locale)
    try:
        runtime.start()
        if external:
            line.restore()
    except BaseException:
        services.stop()
        raise
    return services
