from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .database import Database
from .about import AboutContentError
from .persona_safety import PersonaReviewUnavailable, PersonaSafetyError
from .repositories import ConflictError, NotFoundError, Repository, RepositoryError
from .schemas import CustomItemPayload, SettingsPayload, TargetPayload


class MonitorController(Protocol):
    def start(self) -> bool: ...
    def stop(self) -> bool: ...
    def snapshot(self) -> dict[str, Any]: ...


class PersonaValidator(Protocol):
    def validate_persona(self, text: str, settings: dict[str, Any]) -> None: ...


class AboutLoader(Protocol):
    def load(self) -> str: ...


def _target_for_api(target: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": target["id"],
        "name": target["name"],
        "ageGroup": target["age_group"],
        "gender": target["gender"],
        "personaId": target["persona_id"],
        "personaSource": target["persona_source"],
        "weaponId": target["weapon_id"],
        "weaponSource": target["weapon_source"],
        "replyEnabled": target["reply_enabled"],
        "status": target["status"],
        "roundTrips": target["round_trips"],
        "firstReplyAt": target["first_reply_at"],
        "lastReplyAt": target["last_reply_at"],
        "endedAt": target["ended_at"],
    }


def _custom_for_api(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "name": item["name"],
        "text": item["text"],
        "imageDataUrl": item["image_data_url"],
        "sourceBaseId": item["source_base_id"],
        "createdAt": item["created_at"],
        "updatedAt": item["updated_at"],
    }


def _settings_for_api(settings: dict[str, Any]) -> dict[str, Any]:
    return {
        "aiProvider": settings["ai_provider"],
        "openAiApiKey": settings["openai_api_key"],
        "openAiModel": settings["openai_model"],
        "checkIntervalSeconds": settings["check_interval_seconds"],
        "replyDelayMinSeconds": settings["reply_delay_min_seconds"],
        "replyDelayMaxSeconds": settings["reply_delay_max_seconds"],
    }


def _metrics_for_api(metrics: dict[str, int]) -> dict[str, int]:
    return {
        "targetCount": metrics["target_count"],
        "totalRoundTrips": metrics["total_round_trips"],
        "totalDurationMs": metrics["total_duration_ms"],
        "endedCount": metrics["ended_count"],
    }


def create_app(
    database: Database,
    monitor: MonitorController | None = None,
    frontend_dist: str | Path | None = None,
    persona_validator: PersonaValidator | None = None,
    about_loader: AboutLoader | None = None,
) -> FastAPI:
    database.migrate()
    repository = Repository(database)
    app = FastAPI(title="Sweety Local API", version="0.1.0")
    app.state.repository = repository
    app.state.monitor = monitor
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:8890", "http://localhost:8890"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(RepositoryError)
    async def handle_repository_error(_request: Request, exc: RepositoryError) -> JSONResponse:
        status = 409 if isinstance(exc, ConflictError) else 404 if isinstance(exc, NotFoundError) else 400
        code = str(exc) or exc.code
        return JSONResponse(status_code=status, content={"code": code, "message": code})

    @app.exception_handler(PersonaSafetyError)
    async def handle_persona_safety_error(_request: Request, exc: PersonaSafetyError) -> JSONResponse:
        status = 503 if isinstance(exc, PersonaReviewUnavailable) else 422
        return JSONResponse(status_code=status, content={"code": exc.code, "message": exc.code})

    def validate_persona(text: str, settings: dict[str, Any]) -> None:
        if persona_validator is not None:
            persona_validator.validate_persona(text, settings)

    @app.get("/api/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/api/about")
    def about() -> Any:
        if about_loader is None:
            return JSONResponse(status_code=503, content={"code": "about_content_unavailable", "message": "about_content_unavailable"})
        try:
            return {"html": about_loader.load()}
        except AboutContentError:
            return JSONResponse(status_code=503, content={"code": "about_content_unavailable", "message": "about_content_unavailable"})

    @app.get("/api/state")
    def state() -> dict[str, Any]:
        snapshot = monitor.snapshot() if monitor is not None else {"enabled": False}
        return {
            "version": 1,
            "monitoringEnabled": bool(snapshot.get("enabled")),
            "settings": _settings_for_api(repository.get_settings()),
            "basePersonas": repository.list_base_personas(),
            "targets": [_target_for_api(item) for item in repository.list_targets()],
            "customPersonas": [_custom_for_api(item) for item in repository.list_custom_items("persona")],
            "customWeapons": [_custom_for_api(item) for item in repository.list_custom_items("weapon")],
        }

    @app.put("/api/state")
    def replace_state(payload: dict[str, Any]) -> dict[str, Any]:
        settings = SettingsPayload.model_validate(payload.get("settings", {}))
        settings_values = settings.model_dump()
        incoming_personas = payload.get("customPersonas", [])
        incoming_weapons = payload.get("customWeapons", [])
        existing_personas = {item["id"]: item for item in repository.list_custom_items("persona")}
        for item in incoming_personas:
            parsed = CustomItemPayload.model_validate(item)
            item_id = str(item["id"])
            existing = existing_personas.get(item_id)
            if existing is None or existing["text"] != parsed.text:
                validate_persona(parsed.text, settings_values)

        with repository.database.connect():
            repository.update_settings(settings_values)
            for kind, items in (("persona", incoming_personas), ("weapon", incoming_weapons)):
                for item in items:
                    parsed = CustomItemPayload.model_validate(item)
                    repository.save_custom_item(kind, parsed.model_dump(), str(item["id"]))

            existing_targets = {item["id"]: item for item in repository.list_targets()}
            incoming_target_ids: set[str] = set()
            for item in payload.get("targets", []):
                parsed = TargetPayload.model_validate(item)
                target_id = str(item["id"])
                incoming_target_ids.add(target_id)
                if target_id in existing_targets:
                    repository.update_target(target_id, parsed.model_dump())
                else:
                    repository.create_target({**parsed.model_dump(), "id": target_id})
                if item.get("status") == "ended":
                    repository.end_target(target_id)
                elif target_id in existing_targets and existing_targets[target_id]["status"] == "ended":
                    repository.revive_target(target_id)

            for target_id in set(existing_targets) - incoming_target_ids:
                repository.delete_target(target_id)

            for kind, items in (("persona", incoming_personas), ("weapon", incoming_weapons)):
                incoming_ids = {str(item["id"]) for item in items}
                for existing in repository.list_custom_items(kind):
                    if existing["id"] not in incoming_ids:
                        repository.delete_custom_item(kind, existing["id"])

        return state()

    @app.get("/api/dashboard")
    def dashboard() -> dict[str, int]:
        return _metrics_for_api(repository.dashboard_metrics())

    @app.put("/api/settings")
    def update_settings(payload: SettingsPayload) -> dict[str, Any]:
        values = payload.model_dump()
        return _settings_for_api(repository.update_settings(values))

    @app.post("/api/targets", status_code=201)
    def create_target(payload: TargetPayload) -> dict[str, Any]:
        return _target_for_api(repository.create_target(payload.model_dump()))

    @app.put("/api/targets/{target_id}")
    def update_target(target_id: str, payload: TargetPayload) -> dict[str, Any]:
        return _target_for_api(repository.update_target(target_id, payload.model_dump()))

    @app.patch("/api/targets/{target_id}/reply")
    def update_reply(target_id: str, payload: dict[str, bool]) -> dict[str, Any]:
        return _target_for_api(repository.update_target(target_id, {"reply_enabled": bool(payload.get("replyEnabled"))}))

    @app.post("/api/targets/{target_id}/end")
    def end_target(target_id: str) -> dict[str, Any]:
        return _target_for_api(repository.end_target(target_id))

    @app.post("/api/targets/{target_id}/revive")
    def revive_target(target_id: str) -> dict[str, Any]:
        return _target_for_api(repository.revive_target(target_id))

    @app.delete("/api/targets/{target_id}", status_code=204)
    def delete_target(target_id: str) -> None:
        repository.delete_target(target_id)

    @app.get("/api/targets/{target_id}/export")
    def export_target(target_id: str) -> dict[str, Any]:
        return {
            "target": _target_for_api(repository.get_target(target_id)),
            "messages": repository.list_messages(target_id),
        }

    @app.post("/api/catalog/custom/{kind}", status_code=201)
    def create_custom(kind: str, payload: CustomItemPayload) -> dict[str, Any]:
        if kind not in {"persona", "weapon"}:
            raise NotFoundError("catalog_kind_not_found")
        if kind == "persona":
            validate_persona(payload.text, repository.get_settings())
        return _custom_for_api(repository.save_custom_item(kind, payload.model_dump()))

    @app.put("/api/catalog/custom/{kind}/{item_id}")
    def update_custom(kind: str, item_id: str, payload: CustomItemPayload) -> dict[str, Any]:
        if kind not in {"persona", "weapon"}:
            raise NotFoundError("catalog_kind_not_found")
        if kind == "persona":
            validate_persona(payload.text, repository.get_settings())
        return _custom_for_api(repository.save_custom_item(kind, payload.model_dump(), item_id))

    @app.delete("/api/catalog/custom/{kind}/{item_id}", status_code=204)
    def delete_custom(kind: str, item_id: str) -> None:
        if kind not in {"persona", "weapon"}:
            raise NotFoundError("catalog_kind_not_found")
        repository.delete_custom_item(kind, item_id)

    @app.get("/api/monitor/status")
    def monitor_status() -> dict[str, Any]:
        return monitor.snapshot() if monitor is not None else {"enabled": False, "testMode": False, "status": "not_configured"}

    @app.post("/api/monitor/start")
    def monitor_start() -> Any:
        if monitor is None:
            return JSONResponse(status_code=503, content={"code": "monitor_not_configured", "message": "monitor_not_configured"})
        monitor.start()
        return monitor.snapshot()

    @app.post("/api/monitor/stop")
    def monitor_stop() -> Any:
        if monitor is None:
            return JSONResponse(status_code=503, content={"code": "monitor_not_configured", "message": "monitor_not_configured"})
        monitor.stop()
        return monitor.snapshot()

    if frontend_dist is not None and Path(frontend_dist).is_dir():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app
