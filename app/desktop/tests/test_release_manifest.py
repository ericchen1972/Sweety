import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("release_manifest", Path(__file__).resolve().parents[2] / "tools/set_update_release.py")


def load_module():
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_publishing_one_platform_preserves_other_platform_and_legacy_fields():
    module = load_module()
    original = {"latestVersion": "2.0.2", "downloads": {"windows": "https://example.test/old.exe"},
                "platforms": {"macos": {"latestVersion": "2.0.2", "downloadUrl": "https://example.test/mac.dmg"}}}
    result = module.with_release(original, "windows", "2.0.3", "https://example.test/win.exe")
    assert result["platforms"]["macos"] == original["platforms"]["macos"]
    assert result["latestVersion"] == "2.0.2"
    assert result["downloads"] == original["downloads"]
    assert "windows" not in original["platforms"]
    assert result["platforms"]["windows"]["latestVersion"] == "2.0.3"


@pytest.mark.parametrize("platform,version,url", [("linux", "2.0.3", "https://example.test"),
                                                  ("windows", "bad", "https://example.test"),
                                                  ("macos", "2.0.3", "http://example.test")])
def test_invalid_release_is_rejected(platform, version, url):
    with pytest.raises(ValueError):
        load_module().with_release({}, platform, version, url)
