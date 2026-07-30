from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler

from sweety_app.diagnostics import configure_diagnostics, log_event


def test_configure_diagnostics_writes_rotating_json_events(tmp_path):
    log_path = tmp_path / "logs" / "sweety.log"
    logger = configure_diagnostics(log_path, enabled=True)

    log_event(logger, "test_event", target="Rose", action="skip")
    for handler in logger.handlers:
        handler.flush()

    payload = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert payload["timestamp"].endswith("+00:00")
    assert payload["event"] == "test_event"
    assert payload["target"] == "Rose"
    assert payload["action"] == "skip"
    assert any(
        isinstance(handler, RotatingFileHandler)
        and handler.maxBytes == 2_000_000
        and handler.backupCount == 3
        for handler in logger.handlers
    )

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    logging.Logger.manager.loggerDict.pop(logger.name, None)


def test_disabled_diagnostics_does_not_create_or_write_log(tmp_path):
    log_path = tmp_path / "logs" / "sweety.log"
    logger = configure_diagnostics(log_path, enabled=False)

    log_event(logger, "must_not_be_written", raw_response="private conversation")

    assert not log_path.exists()
