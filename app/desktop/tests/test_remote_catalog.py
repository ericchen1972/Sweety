from __future__ import annotations

from sweety_app.database import Database
from sweety_app.remote_catalog import sync_remote_catalog
from sweety_app.repositories import Repository


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("server error")

    def json(self) -> dict:
        return self.payload


class FakeSession:
    def __init__(self, response: FakeResponse | Exception) -> None:
        self.response = response
        self.calls: list[dict] = []

    def get(self, url: str, **kwargs):
        self.calls.append({"url": url, **kwargs})
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def make_repo(tmp_path) -> Repository:
    database = Database(tmp_path / "remote.sqlite3")
    database.migrate()
    return Repository(database)


def remote_payload() -> dict:
    return {
        "systemPromptTemplate": "遠端 prompt {persona_text} {total_messages}",
        "basePersonas": [
            {
                "id": "remote-persona",
                "ageGroup": "35-50",
                "gender": "female",
                "name": {"zh-TW": "遠端人設", "en": "Remote Persona", "ja": "リモートペルソナ"},
                "content": {"zh-TW": "完整人物資料與風格內容", "en": "Complete character and style content", "ja": "完全な人物情報とスタイル"},
                "image": "/images/personas/remote.jpg",
            }
        ],
    }


def test_sync_remote_catalog_updates_local_cache(tmp_path):
    repo = make_repo(tmp_path)
    session = FakeSession(FakeResponse(remote_payload()))

    updated = sync_remote_catalog(repo, "https://example.test/sweety/catalog", session=session)

    assert updated is True
    assert session.calls[0]["timeout"] == 8
    assert session.calls[0]["headers"]["X-Sweety-App"] == "desktop"
    assert session.calls[0]["headers"]["X-Sweety-App-Token"]
    assert repo.get_system_prompt_template() == "遠端 prompt {persona_text} {total_messages}"
    assert repo.get_base_persona_text("remote-persona") == "完整人物資料與風格內容"
    persona = repo.list_base_personas()[0]
    assert persona["content"]["zh-TW"] == "完整人物資料與風格內容"
    assert persona["content"]["ja"] == "完全な人物情報とスタイル"
    assert not ({"summary", "profile", "style", "text"} & set(persona))


def test_sync_remote_catalog_ignores_server_failures(tmp_path):
    repo = make_repo(tmp_path)
    original_prompt = repo.get_system_prompt_template()
    original_personas = repo.list_base_personas()

    updated = sync_remote_catalog(repo, "https://example.test/sweety/catalog", session=FakeSession(RuntimeError("offline")))

    assert updated is False
    assert repo.get_system_prompt_template() == original_prompt
    assert repo.list_base_personas() == original_personas


def test_sync_remote_catalog_ignores_invalid_payloads(tmp_path):
    repo = make_repo(tmp_path)
    original_prompt = repo.get_system_prompt_template()

    updated = sync_remote_catalog(repo, "https://example.test/sweety/catalog", session=FakeSession(FakeResponse({"basePersonas": []})))

    assert updated is False
    assert repo.get_system_prompt_template() == original_prompt


def test_sync_remote_catalog_rejects_payload_without_japanese(tmp_path):
    repo = make_repo(tmp_path)
    original_personas = repo.list_base_personas()
    payload = remote_payload()
    del payload["basePersonas"][0]["content"]["ja"]

    updated = sync_remote_catalog(repo, "https://example.test/sweety/catalog", session=FakeSession(FakeResponse(payload)))

    assert updated is False
    assert repo.list_base_personas() == original_personas
