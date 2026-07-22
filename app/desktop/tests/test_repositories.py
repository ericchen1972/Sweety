from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import pytest

from sweety_app.database import Database
from sweety_app.repositories import ConflictError, Repository


@pytest.fixture
def repo(tmp_path):
    database = Database(tmp_path / "sweety.sqlite3")
    database.migrate()
    return Repository(database)


def target_payload(name: str = "LINE 完整名稱", reply_enabled: bool = True) -> dict:
    return {
        "name": name,
        "age_group": "20-35",
        "gender": "female",
        "persona_id": "cautious-accounting-assistant",
        "persona_source": "base",
        "weapon_id": "one-step-at-a-time",
        "weapon_source": "base",
        "reply_enabled": reply_enabled,
    }


def test_default_settings_are_created(repo):
    assert repo.get_settings() == {
        "ai_provider": "sweety",
        "openai_api_key": "",
        "openai_model": "gpt-5.5",
        "check_interval_seconds": 10,
        "reply_delay_min_seconds": 15,
        "reply_delay_max_seconds": 45,
    }


def test_prompt_and_base_personas_are_seeded_locally(repo):
    prompt = repo.get_system_prompt_template()
    personas = repo.list_base_personas()

    assert "{persona_text}" in prompt
    assert "{total_messages}" in prompt
    assert len(personas) == 24
    for age_group in ("20-35", "35-50", "50-65", "65+"):
        group = [item for item in personas if item["ageGroup"] == age_group]
        assert len(group) == 6
        assert sum(item["gender"] == "female" for item in group) == 3
        assert sum(item["gender"] == "male" for item in group) == 3
    content = repo.get_base_persona_text("cautious-accounting-assistant")
    assert content.startswith("人物資料")
    assert "與母親妹妹居住在新北市板橋" in content
    assert "你不是詐騙吧？我朋友被騙過，好可怕.." in content


def test_cached_remote_catalog_replaces_local_prompt_and_base_personas(repo):
    repo.replace_remote_catalog(
        system_prompt_template="遠端任務：{persona_text} / {total_messages}",
        base_personas=[
            {
                "id": "remote-persona",
                "ageGroup": "35-50",
                "gender": "female",
                "name": {"zh-TW": "遠端人設", "en": "Remote Persona"},
                "content": {"zh-TW": "遠端完整文字", "en": "Remote full text"},
                "image": "/images/personas/remote.jpg",
            }
        ],
    )

    assert repo.get_system_prompt_template() == "遠端任務：{persona_text} / {total_messages}"
    assert repo.get_base_persona_text("remote-persona") == "遠端完整文字"
    assert repo.list_base_personas() == [
        {
            "id": "remote-persona",
            "ageGroup": "35-50",
            "gender": "female",
            "name": {"zh-TW": "遠端人設", "en": "Remote Persona"},
            "content": {"zh-TW": "遠端完整文字", "en": "Remote full text"},
            "image": "/images/personas/remote.jpg",
        }
    ]


def test_monitor_targets_require_active_and_reply_enabled(repo):
    enabled = repo.create_target(target_payload(name="A", reply_enabled=True))
    repo.create_target(target_payload(name="B", reply_enabled=False))
    ended = repo.create_target(target_payload(name="C", reply_enabled=True))
    repo.end_target(ended["id"])

    assert [item["id"] for item in repo.list_monitor_targets()] == [enabled["id"]]


def test_target_names_are_unique_after_trimming(repo):
    repo.create_target(target_payload(name="王小明✨"))
    with pytest.raises(ConflictError, match="duplicate_target_name"):
        repo.create_target(target_payload(name="  王小明✨  "))


def test_end_and_revive_keep_assignment_but_disable_reply(repo):
    created = repo.create_target(target_payload())
    ended = repo.end_target(created["id"])
    revived = repo.revive_target(created["id"])

    assert ended["status"] == "ended"
    assert ended["reply_enabled"] is False
    assert revived["status"] == "active"
    assert revived["reply_enabled"] is False
    assert revived["persona_id"] == created["persona_id"]
    assert revived["weapon_id"] == created["weapon_id"]


def test_referenced_custom_item_cannot_be_deleted_even_when_target_ended(repo):
    persona = repo.save_custom_item("persona", {"name": "我的人設", "text": "內容", "image_data_url": None, "source_base_id": None})
    payload = target_payload()
    payload.update({"persona_id": persona["id"], "persona_source": "custom"})
    target = repo.create_target(payload)
    repo.end_target(target["id"])

    with pytest.raises(ConflictError, match="custom_item_in_use"):
        repo.delete_custom_item("persona", persona["id"])


def test_messages_are_ordered_and_metrics_use_first_and_last_ai_reply(repo):
    target = repo.create_target(target_payload())
    start = datetime(2026, 7, 21, 8, tzinfo=timezone.utc)
    repo.add_message(target["id"], "scammer", "你好", start.isoformat())
    repo.add_message(target["id"], "assistant", "你好", start.isoformat())
    repo.add_message(target["id"], "scammer", "在嗎", (start + timedelta(hours=2)).isoformat())
    repo.add_message(target["id"], "assistant", "在", (start + timedelta(hours=2)).isoformat())

    messages = repo.list_messages(target["id"])
    refreshed = repo.get_target(target["id"])
    metrics = repo.dashboard_metrics()

    assert [message["role"] for message in messages] == ["scammer", "assistant", "scammer", "assistant"]
    assert refreshed["round_trips"] == 2
    assert metrics["total_round_trips"] == 2
    assert metrics["total_duration_ms"] == 2 * 60 * 60 * 1000


def test_record_exchange_writes_both_messages_and_counts_one_round_trip(repo):
    target = repo.create_target(target_payload())

    repo.record_exchange(target["id"], "對方訊息", "AI 回覆")

    assert [(item["role"], item["content"]) for item in repo.list_messages(target["id"])] == [
        ("scammer", "對方訊息"),
        ("assistant", "AI 回覆"),
    ]
    assert repo.get_target(target["id"])["round_trips"] == 1


def test_installation_id_is_stable_and_is_a_uuid(repo):
    first = repo.get_or_create_installation_id()
    second = repo.get_or_create_installation_id()

    assert first == second
    assert str(uuid.UUID(first)) == first


def test_whole_duration_hours_truncates_successful_reply_duration(repo):
    target = repo.create_target(target_payload())
    start = datetime(2026, 7, 21, 8, tzinfo=timezone.utc)
    repo.add_message(target["id"], "assistant", "第一則成功回覆", start.isoformat())
    repo.add_message(
        target["id"],
        "assistant",
        "最後一則成功回覆",
        (start + timedelta(hours=2, minutes=59, seconds=59)).isoformat(),
    )

    assert repo.whole_duration_hours() == 2
