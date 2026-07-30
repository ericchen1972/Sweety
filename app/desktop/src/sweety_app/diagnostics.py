from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


LOGGER_NAME = "sweety"
MAX_LOG_BYTES = 2_000_000
LOG_BACKUP_COUNT = 3
_diagnostics_enabled = False


def configure_diagnostics(log_path: str | Path, *, enabled: bool) -> logging.Logger:
    global _diagnostics_enabled
    _diagnostics_enabled = enabled
    path = Path(log_path)
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for existing in list(logger.handlers):
        if getattr(existing, "_sweety_diagnostics", False):
            logger.removeHandler(existing)
            existing.close()

    if not enabled:
        return logger

    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path,
        maxBytes=MAX_LOG_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler._sweety_diagnostics = True
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    exc_info: bool = False,
    **fields: Any,
) -> None:
    if not _diagnostics_enabled:
        return
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "pid": os.getpid(),
        "thread": threading.current_thread().name,
        **fields,
    }
    logger.log(
        level,
        json.dumps(payload, ensure_ascii=False, default=str, separators=(",", ":")),
        exc_info=exc_info,
    )
