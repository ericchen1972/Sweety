from __future__ import annotations

import ast
from pathlib import Path


DESKTOP_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = DESKTOP_DIR / "src" / "sweety_app"


def test_startup_schedules_catalog_sync_before_metrics_report():
    module = ast.parse((SOURCE_DIR / "__main__.py").read_text())
    main = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "main")

    catalog_sync_line = next(
        node.lineno
        for node in ast.walk(main)
        if isinstance(node, ast.Name) and node.id == "sync_remote_catalog"
    )
    metrics_report_line = next(
        node.lineno
        for node in ast.walk(main)
        if isinstance(node, ast.Name) and node.id == "start_metrics_reporting"
    )

    assert catalog_sync_line < metrics_report_line


def test_metrics_config_has_no_catalog_token_fallback():
    config_source = (SOURCE_DIR / "config.py").read_text()
    metrics_assignment = next(
        line.strip()
        for line in config_source.splitlines()
        if line.startswith("SWEETY_METRICS_APP_TOKEN =")
    )

    assert 'os.getenv("SWEETY_METRICS_APP_TOKEN", "")' in metrics_assignment
    assert "SWEETY_APP_TOKEN" not in metrics_assignment.replace("SWEETY_METRICS_APP_TOKEN", "")
    assert "sweety-desktop-catalog-v1" not in metrics_assignment


def test_packaging_injects_build_credentials_without_defaults():
    spec_source = (DESKTOP_DIR / "Sweety.spec").read_text()
    config_source = (SOURCE_DIR / "config.py").read_text()

    assert '"SWEETY_AGNES_KEY": os.getenv("SWEETY_AGNES_KEY", "").strip()' in spec_source
    assert '"SWEETY_METRICS_APP_TOKEN": os.getenv("SWEETY_METRICS_APP_TOKEN", "").strip()' in spec_source
    assert '"LSEnvironment": app_environment' in spec_source
    assert "SWEETY_APP_TOKEN" not in spec_source
    assert "_EMBEDDED_AGNES_KEY_B64" not in config_source
    assert "base64.b64decode" not in config_source
    assert "sk-" not in config_source
