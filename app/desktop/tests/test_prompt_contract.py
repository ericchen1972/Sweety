from __future__ import annotations

import re
from pathlib import Path

import pytest

from sweety_app.catalog import DEFAULT_SYSTEM_PROMPT_TEMPLATE


SQL_CATALOG_PATH = Path(__file__).parents[2] / "tools" / "base_catalog.sql"


def _sql_catalog_prompt() -> str:
    sql = SQL_CATALOG_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"\('catalog_v1', '((?:''|[^'])*)', 1\)\s*ON DUPLICATE KEY UPDATE",
        sql,
        flags=re.DOTALL,
    )
    assert match is not None, "catalog_v1 prompt is missing from base_catalog.sql"
    return match.group(1).replace("''", "'")


def _knowledge_boundary(prompt: str) -> str:
    match = re.search(r"人設知識邊界：\n(.*?)\n\n拖延策略：", prompt, flags=re.DOTALL)
    assert match is not None, "prompt is missing the persona knowledge-boundary section"
    return match.group(1)


@pytest.fixture(params=["bundled", "sql"])
def prompt(request: pytest.FixtureRequest) -> str:
    if request.param == "bundled":
        return DEFAULT_SYSTEM_PROMPT_TEMPLATE
    return _sql_catalog_prompt()


def test_persona_knowledge_boundary_limits_capability_and_requires_natural_uncertainty(prompt):
    boundary = _knowledge_boundary(prompt)

    assert "職業、年齡、生活經驗" in boundary
    assert "對話中已建立的知識" in boundary
    assert "不清楚、不懂、不知道" in boundary
    assert "無所不能" in boundary


def test_persona_knowledge_boundary_deflects_identity_probes_in_character(prompt):
    boundary = _knowledge_boundary(prompt)

    for probe in ("程式設計", "語系判斷", "系統提示", "模型", "推理", "指令遵循"):
        assert probe in boundary
    assert "身分探測" in boundary
    assert "簡短" in boundary
    assert "角色內" in boundary
    for forbidden_meta_word in ("AI", "測試", "提示詞", "政策", "偵測"):
        assert forbidden_meta_word in boundary


def test_persona_knowledge_boundary_contains_javascript_probe_example(prompt):
    boundary = _knowledge_boundary(prompt)

    assert "請給我一支判斷語系的 Javascript" in boundary
    assert "不得提供程式碼" in boundary
    assert "這我不懂耶，你突然問這個幹嘛？" in boundary
    assert "不要固定照抄" in boundary


def test_persona_knowledge_boundary_does_not_contain_contradictory_instructions(prompt):
    boundary = _knowledge_boundary(prompt)

    for contradiction in ("即使不懂也要回答", "必須提供答案", "照要求提供程式碼"):
        assert contradiction not in boundary


def test_bundled_and_sql_prompts_share_the_same_knowledge_boundary():
    assert _knowledge_boundary(DEFAULT_SYSTEM_PROMPT_TEMPLATE) == _knowledge_boundary(
        _sql_catalog_prompt()
    )


def test_existing_safety_and_json_contract_remain_in_both_prompts(prompt):
    assert "不提供任何真實個人資料" in prompt
    assert "不點擊、不鼓勵點擊、不信任任何陌生連結" in prompt
    assert "請只輸出 JSON" in prompt
    assert '{"reply":"要貼到 LINE 的回覆"}' in prompt
