import importlib

from sweety_app.config import LOGO_PATH, PROJECT_DIR, normalize_locale


def test_traditional_chinese_locale_variants_use_zh_tw():
    assert normalize_locale("zh-TW") == "zh-TW"
    assert normalize_locale("zh_Hant_TW") == "zh-TW"
    assert normalize_locale("zh-Hant") == "zh-TW"
    assert normalize_locale("zh-CN") == "en"
    assert normalize_locale("ja-JP") == "en"


def test_agnes_key_is_empty_without_environment(monkeypatch):
    with monkeypatch.context() as patch:
        patch.delenv("SWEETY_AGNES_KEY", raising=False)
        config = importlib.reload(importlib.import_module("sweety_app.config"))
        assert config.BUNDLED_AGNES_KEY == ""
    importlib.reload(config)


def test_agnes_key_comes_only_from_environment(monkeypatch):
    with monkeypatch.context() as patch:
        patch.setenv("SWEETY_AGNES_KEY", "test-agnes-key")
        config = importlib.reload(importlib.import_module("sweety_app.config"))
        assert config.BUNDLED_AGNES_KEY == "test-agnes-key"
    importlib.reload(config)


def test_logo_uses_public_web_asset():
    assert LOGO_PATH == PROJECT_DIR / "web" / "images" / "logo.png"
