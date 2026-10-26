from __future__ import annotations

import json
import logging
from types import SimpleNamespace

import httpx
import pytest
from openai import APITimeoutError
from pydantic import ValidationError

import sweety_app.ai as ai_module
from sweety_app.ai import AiClient, AiError, AiTimeoutError, build_messages, contains_external_link
from sweety_app.diagnostics import configure_diagnostics
from sweety_app.catalog import DEFAULT_SYSTEM_PROMPT_TEMPLATE


def target_payload(persona_id: str = "cautious-accounting-assistant") -> dict:
    return {
        "persona_id": persona_id,
        "persona_source": "base",
        "weapon_id": "one-step-at-a-time",
        "weapon_source": "base",
    }


def settings(provider: str = "sweety") -> dict:
    return {
        "ai_provider": provider,
        "agnes_api_key": "agnes-test",
        "openai_api_key": "openai-test",
        "openai_model": "gpt-5.5",
    }


def decision_json(
    *,
    incoming_summary: str = "你好",
    msg_reply: str = "怎麼了？",
) -> str:
    return json.dumps(
        {
            "incoming_summary": incoming_summary,
            "msg_reply": msg_reply,
        },
        ensure_ascii=False,
    )


def test_prompt_isolates_persona_and_sends_role_preserving_text_history():
    history=[{'role':'scammer' if i%2==0 else 'assistant','content':str(i)} for i in range(30)]
    messages=build_messages(system_prompt_template='人設 {persona_text} 數量 {total_messages}',
        persona_text='慢熟',incoming_messages=[{'id':'new','text':'你好'}],history=history,total_messages=86)
    assert '慢熟' not in messages[0]['content']
    assert '慢熟' in messages[1]['content'] and '不可信' in messages[1]['content']
    assert '不得提供任何網址' in messages[0]['content']
    assert len(messages[2:-1])==6
    assert messages[2]=={'role':'user','content':'24'}
    assert messages[3]=={'role':'assistant','content':'25'}
    assert '你好' in messages[-1]['content'] and 'image_url' not in str(messages)


def test_bundled_reply_language_contract_is_not_duplicated_in_model_message():
    messages = build_messages(
        system_prompt_template=DEFAULT_SYSTEM_PROMPT_TEMPLATE,
        persona_text="慢熟的會計助理",
        incoming_messages=[{"id":"new","text":"你好"}],
        history=[],
        total_messages=0,
    )

    assert messages[0]["content"].count("回覆語言：") == 1


class FakeRepository:
    def get_system_prompt_template(self) -> str:
        return "遠端系統提示：{persona_text}，總數 {total_messages}"

    def get_base_persona_text(self, item_id: str) -> str:
        assert item_id == "remote-persona"
        return "遠端人設文字"

    def get_custom_item(self, kind: str, item_id: str) -> dict:
        raise AssertionError("custom item should not be used")


class FakeStructuredClientFactory:
    def __init__(self, results, raw_contents: str | list[str] | None = None) -> None:
        self.results = results if isinstance(results, list) else [results]
        if isinstance(raw_contents, list):
            self.raw_contents = raw_contents
        elif raw_contents is None:
            self.raw_contents = []
        else:
            self.raw_contents = [raw_contents]
        self.client_calls: list[dict] = []
        self.parse_calls: list[dict] = []

    def __call__(self, **kwargs):
        self.client_calls.append(kwargs)
        factory = self

        def parse(**parse_kwargs):
            factory.parse_calls.append(parse_kwargs)
            index = min(len(factory.parse_calls) - 1, len(factory.results) - 1)
            result = factory.results[index]
            if isinstance(result, Exception):
                raise result
            if factory.raw_contents:
                content = factory.raw_contents[min(index, len(factory.raw_contents) - 1)]
            elif hasattr(result, "model_dump_json"):
                content = result.model_dump_json()
            else:
                content = None
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(parsed=result, content=content))]
            )

        return SimpleNamespace(
            beta=SimpleNamespace(
                chat=SimpleNamespace(
                    completions=SimpleNamespace(parse=parse),
                )
            )
        )


def provider_timeout() -> APITimeoutError:
    return APITimeoutError(
        request=httpx.Request("POST", "https://example.test/v1/chat/completions")
    )


def test_generate_reply_surfaces_timeout_after_existing_retries_are_exhausted(tmp_path):
    factory = FakeStructuredClientFactory([provider_timeout(), provider_timeout()])
    client = AiClient(client_factory=factory, agnes_key="agnes-test")

    with pytest.raises(AiTimeoutError, match="timed out"):
        client.generate_reply(
            target=target_payload(),
            incoming_messages=[{"id":"new","text":"你好"}],
            history=[],
            total_messages=0,
            settings=settings(),
        )

    assert len(factory.parse_calls) == 2


def test_generate_reply_hides_transient_timeout_when_retry_succeeds(tmp_path):
    result = ai_module.ReplyDecision(incoming_summary="新訊息", msg_reply="正常回覆")
    factory = FakeStructuredClientFactory([provider_timeout(), result])
    client = AiClient(client_factory=factory, agnes_key="agnes-test")

    assert client.generate_reply(
        target=target_payload(),
        incoming_messages=[{"id":"new","text":"你好"}],
        history=[],
        total_messages=0,
        settings=settings(),
    ) == result
    assert len(factory.parse_calls) == 2


@pytest.mark.parametrize(
    ("provider", "expected_base_url", "expected_model"),
    [
        ("sweety", "https://apihub.agnes-ai.com/v1", "agnes-3.0-flash"),
        ("openai", "https://api.openai.com/v1", "gpt-5.5"),
    ],
)
def test_provider_routing_uses_strict_schema_with_text(
    tmp_path,
    provider,
    expected_base_url,
    expected_model,
):
    result = ai_module.ReplyDecision(incoming_summary="你好", msg_reply="測試回覆")
    factory = FakeStructuredClientFactory(result)
    client = AiClient(client_factory=factory, agnes_key="agnes-test")

    decision = client.generate_reply(
        target=target_payload(),
        incoming_messages=[{"id":"new","text":"你好"}],
        history=[],
        total_messages=0,
        settings=settings(provider),
    )

    assert decision == result
    assert factory.client_calls[0] == {
        "api_key": "agnes-test" if provider == "sweety" else "openai-test",
        "base_url": expected_base_url,
        "timeout": 45,
    }
    request = factory.parse_calls[0]
    assert request["model"] == expected_model
    assert "temperature" not in request
    assert request["response_format"] is ai_module.ReplyDecision
    schema = request["response_format"].model_json_schema()
    assert set(schema["required"]) == {"incoming_summary", "msg_reply"}
    assert schema["additionalProperties"] is False
    assert isinstance(request['messages'][-1]['content'],str)
    assert '你好' in request['messages'][-1]['content']
    assert 'image_url' not in str(request['messages'])


def test_ai_raw_response_is_logged_when_diagnostics_are_enabled(tmp_path):
    log_path = tmp_path / "sweety.log"
    configure_diagnostics(log_path, enabled=True)
    raw_content = decision_json(
        incoming_summary="對方說 **test5 附近**",
        msg_reply="我知道了",
    )
    result = ai_module.ReplyDecision(
        incoming_summary="對方說 **test5 附近**",
        msg_reply="我知道了",
    )
    client = AiClient(
        client_factory=FakeStructuredClientFactory(result, raw_contents=raw_content),
        agnes_key="agnes-test",
    )

    client.generate_reply(
        target=target_payload(),
        incoming_messages=[{"id":"new","text":"你好"}],
        history=[],
        total_messages=0,
        settings=settings(),
    )

    for handler in logging.getLogger("sweety").handlers:
        handler.flush()
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    raw_event = next(event for event in events if event["event"] == "ai_raw_response")
    assert raw_event["content"] == raw_content
    assert raw_event["model"] == "agnes-3.0-flash"

    configure_diagnostics(log_path, enabled=False)


def test_generate_reply_uses_cached_system_prompt_and_base_persona(tmp_path):
    factory = FakeStructuredClientFactory(
        ai_module.ReplyDecision(incoming_summary="你好", msg_reply="遠端回覆")
    )
    client = AiClient(client_factory=factory, agnes_key="agnes-test", repository=FakeRepository())

    decision = client.generate_reply(
        target=target_payload("remote-persona"),
        incoming_messages=[{"id":"new","text":"你好"}],
        history=[],
        total_messages=12,
        settings=settings(),
    )

    assert decision.msg_reply == "遠端回覆"
    messages = factory.parse_calls[0]["messages"]
    assert "遠端人設文字" not in messages[0]["content"]
    assert "總數 12" in messages[0]["content"]
    assert "遠端人設文字" in messages[1]["content"]


def test_reply_decision_preserves_one_condensed_visible_batch():
    decision = ai_module.ReplyDecision(
        incoming_summary="  對方先問網站進度，接著傳了一張貼圖，最後補上一張版面截圖  ",
        msg_reply="收到",
    )

    assert decision.incoming_summary == "對方先問網站進度，接著傳了一張貼圖，最後補上一張版面截圖"
    assert decision.msg_reply == "收到"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"incoming_summary": "你好"},
        {"msg_reply": "收到"},
        {"incoming_summary": " ", "msg_reply": "收到"},
        {"incoming_summary": "你好", "msg_reply": " "},
        {"action": "reply", "incoming_summary": "你好", "msg_reply": "收到"},
        {"action": "skip", "incoming_summary": "", "msg_reply": ""},
    ],
)
def test_reply_decision_schema_rejects_invalid_or_extra_fields(payload):
    with pytest.raises(ValidationError):
        ai_module.ReplyDecision.model_validate(payload)


def test_missing_structured_result_is_rejected_after_one_retry(tmp_path):
    factory = FakeStructuredClientFactory([None, None])
    client = AiClient(client_factory=factory, agnes_key="agnes-test")

    with pytest.raises(AiError, match="invalid"):
        client.generate_reply(
            target=target_payload(),
            incoming_messages=[{"id":"new","text":"你好"}],
            history=[],
            total_messages=0,
            settings=settings(),
        )
    assert len(factory.parse_calls) == 2


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


def test_link_bearing_reply_is_regenerated_once(tmp_path):
    factory = FakeStructuredClientFactory(
        [
            ai_module.ReplyDecision(incoming_summary="你好", msg_reply="請看 https://example.com"),
            ai_module.ReplyDecision(incoming_summary="你好", msg_reply="你可以先說明一下嗎？"),
        ]
    )
    client = AiClient(client_factory=factory, agnes_key="agnes-test")

    decision = client.generate_reply(
        target=target_payload(),
        incoming_messages=[{"id":"new","text":"你好"}],
        history=[],
        total_messages=0,
        settings=settings(),
    )

    assert decision.msg_reply == "你可以先說明一下嗎？"
    assert len(factory.parse_calls) == 2


def test_two_link_bearing_replies_are_rejected(tmp_path):
    result = ai_module.ReplyDecision(incoming_summary="你好", msg_reply="請看 example.com")
    client = AiClient(client_factory=FakeStructuredClientFactory([result, result]), agnes_key="agnes-test")

    with pytest.raises(AiError, match="unsafe link"):
        client.generate_reply(
            target=target_payload(),
            incoming_messages=[{"id":"new","text":"你好"}],
            history=[],
            total_messages=0,
            settings=settings(),
        )


def test_ai_persona_classifier_uses_fixed_policy_and_structured_result():
    factory = FakeStructuredClientFactory(
        ai_module.PersonaClassification(allowed=True),
        raw_contents='{"allowed":true}',
    )
    client = AiClient(client_factory=factory, agnes_key="agnes-test")

    client.validate_persona("謹慎而慢熟的會計助理。", settings())

    request = factory.parse_calls[0]
    assert "temperature" not in request
    assert "不可信資料" in request["messages"][0]["content"]
    assert "謹慎而慢熟的會計助理" in request["messages"][1]["content"]
    assert request["response_format"] is ai_module.PersonaClassification


def test_errors_do_not_include_api_keys(tmp_path):
    client = AiClient(
        client_factory=FakeStructuredClientFactory(RuntimeError("provider failed")),
        agnes_key="super-secret-agnes",
    )

    with pytest.raises(AiError) as error:
        client.generate_reply(
            target=target_payload(),
            incoming_messages=[{"id":"new","text":"你好"}],
            history=[],
            total_messages=0,
            settings=settings(),
        )

    assert "super-secret-agnes" not in str(error.value)


def test_rate_limit_is_reported_without_immediate_retry():
    from openai import RateLimitError
    response=httpx.Response(429,request=httpx.Request('POST','https://example.test'))
    factory=FakeStructuredClientFactory(RateLimitError('rate limited',response=response,body=None))
    client=AiClient(client_factory=factory,agnes_key='test')
    with pytest.raises(ai_module.AiRateLimitError):
        client.generate_reply(target=target_payload(),incoming_messages=[{'id':'m','text':'hi'}],history=[],total_messages=0,settings=settings())
    assert len(factory.parse_calls)==1


def test_agnes_requires_user_key_and_uses_configured_model():
    client=AiClient(agnes_key='bundled-key-must-not-be-used')
    with pytest.raises(AiError):client._provider({'ai_provider':'sweety'})
    assert client._provider({'ai_provider':'sweety','agnes_api_key':' user-key ','agnes_model':'agnes-custom'}) == (ai_module.AGNES_BASE_URL,'user-key','agnes-custom')

@pytest.mark.parametrize('limit,expected',[(0,0),(5,5),(30,30)])
def test_configurable_history_count(limit,expected):
    history=[{'role':'user','content':f'history-{i}'} for i in range(40)]
    result=build_messages(system_prompt_template='rules',persona_text='persona',incoming_messages=[],history=history,total_messages=40,history_limit=limit)
    included=[m['content'] for m in result if isinstance(m['content'],str) and m['content'].startswith('history-')]
    assert len(included)==expected
    if expected:assert included[0]==f'history-{40-expected}'
