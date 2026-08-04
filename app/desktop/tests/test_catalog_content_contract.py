from sweety_app.catalog import BASE_PERSONAS, DEFAULT_SYSTEM_PROMPT_TEMPLATE


SHARED_ZH = "你只熟悉自己生活與工作經驗內的事情"
SHARED_EN = "Stay within what this person could reasonably know from work and ordinary life"


def test_base_personas_do_not_repeat_shared_system_policy():
    for persona in BASE_PERSONAS:
        assert SHARED_ZH not in persona["content"]["zh-TW"]
        assert SHARED_EN not in persona["content"]["en"]


def test_base_personas_include_complete_japanese_localization():
    assert len(BASE_PERSONAS) == 24
    for persona in BASE_PERSONAS:
        assert persona["name"]["ja"].strip()
        assert len(persona["content"]["ja"].strip()) >= 180

    wang = BASE_PERSONAS[0]
    assert wang["name"]["ja"] == "慎重な経理アシスタント"
    assert "王筱蘭" in wang["content"]["ja"]
    assert "70万台湾ドル" in wang["content"]["ja"]
    assert "詐欺" in wang["content"]["ja"]


def test_system_prompt_retains_knowledge_and_financial_boundaries():
    assert "人設知識邊界" in DEFAULT_SYSTEM_PROMPT_TEMPLATE
    assert "職業、年齡、生活經驗" in DEFAULT_SYSTEM_PROMPT_TEMPLATE
    assert "對方提供投資或賺錢理由時，可以表現出興趣" in DEFAULT_SYSTEM_PROMPT_TEMPLATE
    assert "要繼續問細節、風險、流程、能不能晚點" in DEFAULT_SYSTEM_PROMPT_TEMPLATE
