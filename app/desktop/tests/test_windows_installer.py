import importlib.util
import json
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location('build_windows_installer',
    Path(__file__).resolve().parents[1] / 'build_windows_installer.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


@pytest.fixture
def package(tmp_path):
    for name in ('Sweety.exe', '_internal/runtime/node.exe', '_internal/frontend/index.html',
                 '_internal/assets/panel-background.png'):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'fixture')
    (tmp_path / '_internal/runtime-config.json').write_text(json.dumps({'SWEETY_LOG_ENABLED': '0'}))
    return tmp_path


def test_installer_rejects_diagnostic_build(package):
    (package / '_internal/runtime-config.json').write_text(json.dumps({'SWEETY_LOG_ENABLED': '1'}))
    with pytest.raises(ValueError, match='--logging 0'):
        builder.validate_package(package)


@pytest.mark.parametrize('name', ['sweety.sqlite3', 'private.session', 'sweety.log'])
def test_installer_rejects_accidentally_copied_user_data(package, name):
    (package / name).write_bytes(b'private fixture')
    with pytest.raises(ValueError, match='User data'):
        builder.validate_package(package)


def test_release_package_passes_preflight(package):
    builder.validate_package(package)


def test_upgrade_removes_legacy_images_file_without_removing_directories():
    source = (Path(__file__).resolve().parents[1] / 'Sweety-Setup.iss').read_text(encoding='utf-8')
    assert 'Type: files; Name: "{app}\\_internal\\frontend\\images"' in source
    assert 'filesandordirs' not in source.lower()
