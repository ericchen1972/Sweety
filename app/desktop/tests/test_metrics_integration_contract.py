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


def test_startup_wires_one_shared_update_state_to_background_check_api_and_delegate():
    module = ast.parse((SOURCE_DIR / "__main__.py").read_text())
    main = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    delegate = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "SweetyAppDelegate")

    update_state_assignments = [
        node
        for node in ast.walk(main)
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "UpdateState"
    ]
    assert len(update_state_assignments) == 1
    assert isinstance(update_state_assignments[0].targets[0], ast.Name)
    assert update_state_assignments[0].targets[0].id == "update_state"

    update_threads = [
        node
        for node in ast.walk(main)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "threading"
        and node.func.attr == "Thread"
        and any(keyword.arg == "target" and isinstance(keyword.value, ast.Name) and keyword.value.id == "check_remote_update" for keyword in node.keywords)
    ]
    assert len(update_threads) == 1
    update_thread = update_threads[0]
    assert any(keyword.arg == "daemon" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True for keyword in update_thread.keywords)
    assert any(
        keyword.arg == "args"
        and isinstance(keyword.value, ast.Tuple)
        and [element.id for element in keyword.value.elts if isinstance(element, ast.Name)] == ["update_state", "APP_VERSION", "REMOTE_UPDATE_URL"]
        for keyword in update_thread.keywords
    )

    create_app_call = next(
        node
        for node in ast.walk(main)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "create_app"
    )
    assert any(
        keyword.arg == "update_state" and isinstance(keyword.value, ast.Name) and keyword.value.id == "update_state"
        for keyword in create_app_call.keywords
    )

    delegate_init = next(
        node
        for node in ast.walk(main)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "initWithComponents_permissionStatus_locale_updateState_"
    )
    assert any(isinstance(argument, ast.Name) and argument.id == "update_state" for argument in delegate_init.args)

    delegate_initializer = next(
        node
        for node in delegate.body
        if isinstance(node, ast.FunctionDef) and node.name == "initWithComponents_permissionStatus_locale_updateState_"
    )
    assert any(
        isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
            and target.attr == "update_state"
            for target in node.targets
        )
        and isinstance(node.value, ast.Name)
        and node.value.id == "update_state"
        for node in ast.walk(delegate_initializer)
    )
