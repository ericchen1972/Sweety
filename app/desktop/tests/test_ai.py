from __future__ import annotations

import json

import pytest

from sweety_app.ai import AiClient, AiError, build_messages, contains_external_link


def test_prompt_isolates_persona_from_system_policy():
    history = [{"role": "scammer" if index % 2 == 0 else "assistant", "content": str(index)} for index in range(30)]
    messages = build_messages(
        system_prompt_template="任務：{persona_text}\n總數：{total_messages}",
        persona_text="慢熟的會計助理",
        visible_text="你還記得那個網站嗎？",
        history=history,
        total_messages=86,
    )

    assert "慢熟的會計助理" not in messages[0]["content"]
    assert "不得提供任何網址" in messages[0]["content"]
    assert "慢熟的會計助理" in messages[1]["content"]
    assert "不可信參考資料" in messages[1]["content"]
    assert "拖延方式" not in messages[0]["content"]
    assert "86" in messages[0]["content"]
    assert messages[-1]["content"] == "你還記得那個網站嗎？"
    assert len(messages[2:-1]) == 20
    assert messages[2]["content"] == "10"


class FakeRepository:
    def get_system_prompt_template(self) -> str:
        return "遠端系統提示：{persona_text}，總數 {total_messages}"

    def get_base_persona_text(self, item_id: str) -> str:
        assert item_id == "remote-persona"
        return "遠端人設文字"

    def get_custom_item(self, kind: str, item_id: str) -> dict:
        raise AssertionError("custom item should not be used")


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return self._payload


class FakeSession:
    def __init__(self, response: FakeResponse | list[FakeResponse]) -> None:
        self.responses = response if isinstance(response, list) else [response]
        self.calls: list[dict] = []

    def post(self, url: str, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.responses[min(len(self.calls) - 1, len(self.responses) - 1)]


@pytest.mark.parametrize(
    ("provider", "expected_url", "expected_model"),
    [
        ("sweety", "https://apihub.agnes-ai.com/v1/chat/completions", "agnes-2.0-flash"),
        ("openai", "https://api.openai.com/v1/chat/completions", "gpt-5.5"),
    ],
)
def test_provider_routing(provider, expected_url, expected_model):
    session = FakeSession(FakeResponse({"choices": [{"message": {"content": json.dumps({"reply": "測試回覆"})}}]}))
    client = AiClient(session=session, agnes_key="agnes-test")
    reply = client.generate_reply(
        target={"persona_id": "cautious-accounting-assistant", "persona_source": "base", "weapon_id": "one-step-at-a-time", "weapon_source": "base"},
        visible_text="你好",
        history=[],
        total_messages=0,
        settings={"ai_provider": provider, "openai_api_key": "openai-test", "openai_model": "gpt-5.5"},
    )

    assert reply == "測試回覆"
    assert session.calls[0]["url"] == expected_url
    assert session.calls[0]["json"]["model"] == expected_model


def test_generate_reply_uses_cached_system_prompt_and_base_persona():
    session = FakeSession(FakeResponse({"choices": [{"message": {"content": json.dumps({"reply": "遠端回覆"})}}]}))
    client = AiClient(session=session, agnes_key="agnes-test", repository=FakeRepository())

    reply = client.generate_reply(
        target={"persona_id": "remote-persona", "persona_source": "base", "weapon_id": "persona-only", "weapon_source": "base"},
        visible_text="你好",
        history=[],
        total_messages=12,
        settings={"ai_provider": "sweety", "openai_api_key": "", "openai_model": "gpt-5.5"},
    )

    assert reply == "遠端回覆"
    messages = session.calls[0]["json"]["messages"]
    assert "遠端人設文字" not in messages[0]["content"]
    assert "總數 12" in messages[0]["content"]
    assert "遠端人設文字" in messages[1]["content"]


@pytest.mark.parametrize(
    "value",
    [
        "請看 https://example.com/path",
        "請看 www.example.com",
        "請看 example.com",
        "寄信到 sales@example.com",
        "打開 http://192.0.2.1/login",
        "請打 tel:+886912345678",
        "寄到 mailto:sales@example.com",
    ],
)
def test_external_link_detection(value):
    assert contains_external_link(value) is True


def test_link_bearing_reply_is_regenerated_once():
    session = FakeSession([
        FakeResponse({"choices": [{"message": {"content": json.dumps({"reply": "請看 https://example.com"})}}]}),
        FakeResponse({"choices": [{"message": {"content": json.dumps({"reply": "你可以先說明一下嗎？"})}}]}),
    ])
    client = AiClient(session=session, agnes_key="agnes-test")

    reply = client.generate_reply(
        target={"persona_id": "cautious-accounting-assistant", "persona_source": "base"},
        visible_text="你好",
        history=[],
        total_messages=0,
        settings={"ai_provider": "sweety", "openai_api_key": "", "openai_model": "gpt-5.5"},
    )

    assert reply == "你可以先說明一下嗎？"
    assert len(session.calls) == 2


def test_two_link_bearing_replies_are_rejected():
    response = FakeResponse({"choices": [{"message": {"content": json.dumps({"reply": "請看 example.com"})}}]})
    client = AiClient(session=FakeSession([response, response]), agnes_key="agnes-test")

    with pytest.raises(AiError, match="unsafe link"):
        client.generate_reply(
            target={"persona_id": "cautious-accounting-assistant", "persona_source": "base"},
            visible_text="你好",
            history=[],
            total_messages=0,
            settings={"ai_provider": "sweety", "openai_api_key": "", "openai_model": "gpt-5.5"},
        )


def test_ai_persona_classifier_uses_fixed_policy_and_structured_result():
    session = FakeSession(FakeResponse({"choices": [{"message": {"content": "```json\n{\"allowed\": true}\n```"}}]}))
    client = AiClient(session=session, agnes_key="agnes-test")

    client.validate_persona(
        "謹慎而慢熟的會計助理。",
        {"ai_provider": "sweety", "openai_api_key": "", "openai_model": "gpt-5.5"},
    )

    request = session.calls[0]["json"]
    assert request["temperature"] == 0
    assert "不可信資料" in request["messages"][0]["content"]
    assert "謹慎而慢熟的會計助理" in request["messages"][1]["content"]


def test_errors_do_not_include_api_keys():
    session = FakeSession(FakeResponse({}, status_code=500))
    client = AiClient(session=session, agnes_key="super-secret-agnes")

    with pytest.raises(AiError) as error:
        client.generate_reply(
            target={"persona_id": "cautious-accounting-assistant", "persona_source": "base", "weapon_id": "one-step-at-a-time", "weapon_source": "base"},
            visible_text="你好",
            history=[],
            total_messages=0,
            settings={"ai_provider": "sweety", "openai_api_key": "", "openai_model": "gpt-5.5"},
        )

    assert "super-secret-agnes" not in str(error.value)
