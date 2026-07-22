from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from sweety_app.api import create_app
from sweety_app.database import Database


class FakeAboutLoader:
    def load(self):
        return "<main><h1>關於 Sweety</h1></main>"


class FakeUpdateState:
    def __init__(self, snapshot):
        self._snapshot = snapshot

    def snapshot(self):
        return dict(self._snapshot)

    def set_snapshot(self, snapshot):
        self._snapshot = snapshot


class AllowPersonaValidator:
    def __init__(self):
        self.calls = []

    def validate_persona(self, text, settings):
        self.calls.append({"text": text, "settings": settings})


class RejectPersonaValidator:
    def validate_persona(self, text, settings):
        from sweety_app.persona_safety import PersonaRejectedError

        raise PersonaRejectedError("custom_persona_rejected")


@pytest.fixture
def client(tmp_path):
    database = Database(tmp_path / "api.sqlite3")
    return TestClient(create_app(database))


def target_payload(name: str = "LINE 完整名稱") -> dict:
    return {
        "name": name,
        "ageGroup": "20-35",
        "gender": "female",
        "personaId": "cautious-accounting-assistant",
        "personaSource": "base",
        "weaponId": "one-step-at-a-time",
        "weaponSource": "base",
        "replyEnabled": True,
    }


def test_health_and_empty_state(client):
    assert client.get("/api/health").json() == {"ok": True}
    state = client.get("/api/state").json()
    assert state["version"] == 1
    assert state["monitoringEnabled"] is False
    assert state["settings"]["openAiModel"] == "gpt-5.5"
    assert any(item["id"] == "cautious-accounting-assistant" for item in state["basePersonas"])
    assert state["targets"] == []


def test_update_endpoint_reflects_the_same_injected_state_as_it_finishes(tmp_path):
    update_state = FakeUpdateState({"checked": False, "updateAvailable": False})
    client = TestClient(create_app(Database(tmp_path / "updates.sqlite3"), update_state=update_state))

    assert client.get("/api/update").json() == {"checked": False, "updateAvailable": False}

    update_state.set_snapshot({
        "checked": True,
        "updateAvailable": True,
        "latestVersion": "1.0.2",
        "downloads": {"macos": "https://downloads.example.test/Sweety.dmg"},
    })

    assert client.get("/api/update").json() == {
        "checked": True,
        "updateAvailable": True,
        "latestVersion": "1.0.2",
        "downloads": {"macos": "https://downloads.example.test/Sweety.dmg"},
    }


def test_update_endpoint_defaults_to_checked_unavailable_without_state(client):
    response = client.get("/api/update")

    assert response.status_code == 200
    assert response.json() == {"checked": True, "updateAvailable": False}


def test_about_endpoint_returns_sanitized_remote_content(tmp_path):
    client = TestClient(create_app(Database(tmp_path / "about.sqlite3"), about_loader=FakeAboutLoader()))

    response = client.get("/api/about")

    assert response.status_code == 200
    assert response.json() == {"html": "<main><h1>關於 Sweety</h1></main>"}


def test_settings_validation(client):
    response = client.put(
        "/api/settings",
        json={
            "aiProvider": "openai",
            "openAiApiKey": "test-key",
            "openAiModel": "gpt-5.5",
            "checkIntervalSeconds": 12,
            "replyDelayMinSeconds": 20,
            "replyDelayMaxSeconds": 10,
        },
    )
    assert response.status_code == 422


def test_target_lifecycle_and_duplicate_error(client):
    created = client.post("/api/targets", json=target_payload()).json()
    duplicate = client.post("/api/targets", json=target_payload())
    ended = client.post(f"/api/targets/{created['id']}/end").json()
    revived = client.post(f"/api/targets/{created['id']}/revive").json()

    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "duplicate_target_name"
    assert ended["status"] == "ended"
    assert revived["status"] == "active"
    assert revived["replyEnabled"] is False


def test_target_payload_can_omit_weapon_assignment(client):
    payload = target_payload()
    payload.pop("weaponId")
    payload.pop("weaponSource")

    created = client.post("/api/targets", json=payload)

    assert created.status_code == 201
    assert created.json()["weaponId"] == "persona-only"
    assert created.json()["weaponSource"] == "base"


def test_custom_catalog_and_reference_guard(client):
    persona = client.post(
        "/api/catalog/custom/persona",
        json={"name": "我的人設", "text": "內容", "imageDataUrl": None, "sourceBaseId": None},
    ).json()
    payload = target_payload()
    payload.update({"personaId": persona["id"], "personaSource": "custom"})
    client.post("/api/targets", json=payload)

    blocked = client.delete(f"/api/catalog/custom/persona/{persona['id']}")
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "custom_item_in_use"


def test_custom_persona_is_validated_before_save(tmp_path):
    validator = AllowPersonaValidator()
    client = TestClient(create_app(Database(tmp_path / "validated.sqlite3"), persona_validator=validator))

    response = client.post(
        "/api/catalog/custom/persona",
        json={"name": "我的人設", "text": "謹慎而慢熟的會計助理。", "imageDataUrl": None, "sourceBaseId": None},
    )

    assert response.status_code == 201
    assert validator.calls[0]["text"] == "謹慎而慢熟的會計助理。"


def test_rejected_custom_persona_is_not_persisted(tmp_path):
    database = Database(tmp_path / "rejected.sqlite3")
    client = TestClient(create_app(database, persona_validator=RejectPersonaValidator()))

    response = client.post(
        "/api/catalog/custom/persona",
        json={"name": "投資專員", "text": "說服對方投資。", "imageDataUrl": None, "sourceBaseId": None},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "custom_persona_rejected"
    assert client.get("/api/state").json()["customPersonas"] == []


def test_rejected_persona_in_state_snapshot_leaves_state_unchanged(tmp_path):
    database = Database(tmp_path / "rejected-state.sqlite3")
    client = TestClient(create_app(database, persona_validator=RejectPersonaValidator()))
    state = client.get("/api/state").json()
    original_interval = state["settings"]["checkIntervalSeconds"]
    state["settings"]["checkIntervalSeconds"] = 99
    state["customPersonas"] = [{
        "id": "unsafe-persona",
        "name": "投資專員",
        "text": "說服對方投資。",
        "imageDataUrl": None,
        "sourceBaseId": None,
    }]

    response = client.put("/api/state", json=state)
    reloaded = client.get("/api/state").json()

    assert response.status_code == 422
    assert reloaded["settings"]["checkIntervalSeconds"] == original_interval
    assert reloaded["customPersonas"] == []


def test_export_is_json_and_dashboard_uses_persisted_data(client):
    created = client.post("/api/targets", json=target_payload()).json()
    exported = client.get(f"/api/targets/{created['id']}/export").json()
    metrics = client.get("/api/dashboard").json()

    assert exported["target"]["name"] == "LINE 完整名稱"
    assert exported["messages"] == []
    assert metrics["targetCount"] == 1


def test_monitor_endpoints_use_controller(client):
    assert client.get("/api/monitor/status").json()["enabled"] is False
    assert client.post("/api/monitor/start").status_code == 503


def test_client_state_can_be_persisted_as_one_snapshot(client):
    state = client.get("/api/state").json()
    state["targets"] = [{
        "id": "target-client",
        **target_payload("從前端建立"),
        "status": "active",
        "roundTrips": 0,
        "firstReplyAt": None,
        "lastReplyAt": None,
        "endedAt": None,
    }]

    saved = client.put("/api/state", json=state)
    reloaded = client.get("/api/state").json()

    assert saved.status_code == 200
    assert reloaded["targets"][0]["id"] == "target-client"
    assert reloaded["targets"][0]["name"] == "從前端建立"

    state["targets"][0]["status"] = "ended"
    client.put("/api/state", json=state)
    state["targets"][0]["status"] = "active"
    state["targets"][0]["replyEnabled"] = False
    client.put("/api/state", json=state)

    assert client.get("/api/state").json()["targets"][0]["status"] == "active"


def test_state_snapshot_rolls_back_every_change_when_a_later_write_fails(client):
    state = client.get("/api/state").json()
    original_interval = state["settings"]["checkIntervalSeconds"]
    state["settings"]["checkIntervalSeconds"] = 99
    state["targets"] = [
        {"id": "target-one", **target_payload("重複名稱")},
        {"id": "target-two", **target_payload("重複名稱")},
    ]

    response = client.put("/api/state", json=state)
    reloaded = client.get("/api/state").json()

    assert response.status_code == 409
    assert reloaded["settings"]["checkIntervalSeconds"] == original_interval
    assert reloaded["targets"] == []


def test_target_rejects_unknown_catalog_assignments(client):
    payload = target_payload()
    payload["personaId"] = "missing-persona"

    response = client.post("/api/targets", json=payload)

    assert response.status_code == 404
    assert response.json()["code"] == "persona_not_found"
