from __future__ import annotations

import re
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from .catalog import BASE_WEAPON_TEXT
from .database import Database


class RepositoryError(Exception):
    code = "repository_error"


class ConflictError(RepositoryError):
    code = "conflict"


class NotFoundError(RepositoryError):
    code = "not_found"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalized_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    result = dict(row)
    if "reply_enabled" in result:
        result["reply_enabled"] = bool(result["reply_enabled"])
    return result


class Repository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get_settings(self) -> dict[str, Any]:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT ai_provider, openai_api_key, openai_model,
                       check_interval_seconds, reply_delay_min_seconds,
                       reply_delay_max_seconds
                FROM settings WHERE singleton = 1
                """
            ).fetchone()
        return dict(row)

    def get_or_create_installation_id(self) -> str:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT value FROM app_metadata WHERE key = 'installation_id'"
            ).fetchone()
            if row is not None:
                return str(row["value"])
            installation_id = str(uuid.uuid4())
            connection.execute(
                "INSERT INTO app_metadata(key, value) VALUES ('installation_id', ?)",
                (installation_id,),
            )
        return installation_id

    def whole_duration_hours(self) -> int:
        duration_ms = max(0, int(self.dashboard_metrics()["total_duration_ms"]))
        return duration_ms // 3_600_000

    def get_metrics_report_state(self) -> dict[str, int] | None:
        keys = (
            "metrics_baseline_hours",
            "metrics_registered_at",
            "metrics_accepted_hours",
        )
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT key, value FROM app_metadata WHERE key IN (?, ?, ?)",
                keys,
            ).fetchall()
        values = {str(row["key"]): str(row["value"]) for row in rows}
        if set(values) != set(keys):
            return None
        try:
            baseline_hours = int(values["metrics_baseline_hours"])
            registered_at = int(values["metrics_registered_at"])
            accepted_hours = int(values["metrics_accepted_hours"])
        except (TypeError, ValueError):
            return None
        if baseline_hours < 0 or registered_at <= 0 or accepted_hours < baseline_hours:
            return None
        return {
            "baseline_hours": baseline_hours,
            "registered_at": registered_at,
            "accepted_hours": accepted_hours,
        }

    def save_metrics_report_acceptance(self, accepted_hours: int, registered_at: int) -> None:
        accepted_hours = max(0, int(accepted_hours))
        registered_at = int(registered_at)
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT key, value FROM app_metadata
                WHERE key IN (
                    'metrics_baseline_hours',
                    'metrics_registered_at',
                    'metrics_accepted_hours'
                )
                """
            ).fetchall()
            values = {str(row["key"]): str(row["value"]) for row in rows}
            state_is_complete = {
                "metrics_baseline_hours",
                "metrics_registered_at",
                "metrics_accepted_hours",
            } == set(values)
            if state_is_complete:
                try:
                    current_baseline = int(values["metrics_baseline_hours"])
                    current_registered_at = int(values["metrics_registered_at"])
                    current_accepted = int(values["metrics_accepted_hours"])
                except (TypeError, ValueError):
                    state_is_complete = False
                else:
                    state_is_complete = (
                        current_baseline >= 0
                        and current_registered_at > 0
                        and current_accepted >= current_baseline
                    )
            if state_is_complete:
                connection.execute(
                    "UPDATE app_metadata SET value = ? WHERE key = 'metrics_accepted_hours'",
                    (str(max(current_accepted, accepted_hours)),),
                )
                return

            connection.execute(
                """
                DELETE FROM app_metadata
                WHERE key IN (
                    'metrics_baseline_hours',
                    'metrics_registered_at',
                    'metrics_accepted_hours'
                )
                """
            )
            connection.executemany(
                "INSERT INTO app_metadata(key, value) VALUES (?, ?)",
                (
                    ("metrics_baseline_hours", str(accepted_hours)),
                    ("metrics_registered_at", str(registered_at)),
                    ("metrics_accepted_hours", str(accepted_hours)),
                ),
            )

    def update_settings(self, values: dict[str, Any]) -> dict[str, Any]:
        current = self.get_settings()
        current.update(values)
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE settings SET ai_provider = ?, openai_api_key = ?,
                    openai_model = ?, check_interval_seconds = ?,
                    reply_delay_min_seconds = ?, reply_delay_max_seconds = ?
                WHERE singleton = 1
                """,
                (
                    current["ai_provider"], current["openai_api_key"],
                    current["openai_model"], current["check_interval_seconds"],
                    current["reply_delay_min_seconds"], current["reply_delay_max_seconds"],
                ),
            )
        return self.get_settings()

    def get_system_prompt_template(self) -> str:
        with self.database.connect() as connection:
            row = connection.execute("SELECT template FROM system_prompts WHERE singleton = 1").fetchone()
        if row is None:
            raise NotFoundError("system_prompt_not_found")
        return str(row["template"])

    def list_base_personas(self) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM base_personas
                ORDER BY sort_order, id
                """
            ).fetchall()
        return [self._base_persona_for_api(row) for row in rows]

    def get_base_persona_text(self, item_id: str) -> str:
        with self.database.connect() as connection:
            row = connection.execute("SELECT content_zh_tw FROM base_personas WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            raise NotFoundError("persona_not_found")
        return str(row["content_zh_tw"])

    def replace_remote_catalog(self, *, system_prompt_template: str, base_personas: list[dict[str, Any]]) -> None:
        now = utc_now()
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO system_prompts(singleton, template, updated_at)
                VALUES (1, ?, ?)
                ON CONFLICT(singleton) DO UPDATE SET
                    template = excluded.template,
                    updated_at = excluded.updated_at
                """,
                (system_prompt_template, now),
            )
            connection.execute("DELETE FROM base_personas")
            for index, persona in enumerate(base_personas):
                connection.execute(
                    """
                    INSERT INTO base_personas(
                        id, age_group, gender, name_zh_tw, name_en,
                        content_zh_tw, content_en, image, sort_order, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(persona["id"]), str(persona.get("ageGroup", "20-35")), str(persona["gender"]),
                        str(persona["name"]["zh-TW"]), str(persona["name"]["en"]),
                        str(persona["content"]["zh-TW"]), str(persona["content"]["en"]),
                        str(persona["image"]), index, now,
                    ),
                )

    @staticmethod
    def _base_persona_for_api(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "ageGroup": row["age_group"],
            "gender": row["gender"],
            "name": {"zh-TW": row["name_zh_tw"], "en": row["name_en"]},
            "content": {"zh-TW": row["content_zh_tw"], "en": row["content_en"]},
            "image": row["image"],
        }

    def create_target(self, values: dict[str, Any]) -> dict[str, Any]:
        self._validate_assignments(values)
        name = str(values.get("name", "")).strip()
        now = utc_now()
        target_id = str(values.get("id") or f"target-{uuid.uuid4().hex}")
        try:
            with self.database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO targets(
                        id, name, name_key, age_group, gender, persona_id,
                        persona_source, weapon_id, weapon_source, reply_enabled,
                        status, round_trips, first_reply_at, last_reply_at,
                        ended_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', 0, NULL, NULL, NULL, ?, ?)
                    """,
                    (
                        target_id, name, normalized_name(name), values["age_group"],
                        values["gender"], values["persona_id"], values["persona_source"],
                        values["weapon_id"], values["weapon_source"],
                        int(bool(values.get("reply_enabled", False))), now, now,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            if "targets.name_key" in str(exc):
                raise ConflictError("duplicate_target_name") from exc
            raise
        return self.get_target(target_id)

    def get_target(self, target_id: str) -> dict[str, Any]:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM targets WHERE id = ?", (target_id,)).fetchone()
        result = _row(row)
        if result is None:
            raise NotFoundError("target_not_found")
        return result

    def list_targets(self, status: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM targets"
        params: tuple[Any, ...] = ()
        if status is not None:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY created_at, id"
        with self.database.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_row(row) for row in rows]  # type: ignore[misc]

    def list_monitor_targets(self) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM targets WHERE status = 'active' AND reply_enabled = 1 ORDER BY created_at, id"
            ).fetchall()
        return [_row(row) for row in rows]  # type: ignore[misc]

    def update_target(self, target_id: str, values: dict[str, Any]) -> dict[str, Any]:
        current = self.get_target(target_id)
        allowed = {
            "name", "age_group", "gender", "persona_id", "persona_source",
            "weapon_id", "weapon_source", "reply_enabled",
        }
        updated = {**current, **{key: value for key, value in values.items() if key in allowed}}
        self._validate_assignments(updated)
        name = str(updated["name"]).strip()
        try:
            with self.database.connect() as connection:
                connection.execute(
                    """
                    UPDATE targets SET name = ?, name_key = ?, age_group = ?, gender = ?,
                        persona_id = ?, persona_source = ?, weapon_id = ?, weapon_source = ?,
                        reply_enabled = ?, updated_at = ? WHERE id = ?
                    """,
                    (
                        name, normalized_name(name), updated["age_group"], updated["gender"],
                        updated["persona_id"], updated["persona_source"], updated["weapon_id"],
                        updated["weapon_source"], int(bool(updated["reply_enabled"])), utc_now(), target_id,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            if "targets.name_key" in str(exc):
                raise ConflictError("duplicate_target_name") from exc
            raise
        return self.get_target(target_id)

    def _validate_assignments(self, values: dict[str, Any]) -> None:
        for kind, base_items in (("persona", None), ("weapon", BASE_WEAPON_TEXT)):
            item_id = str(values[f"{kind}_id"])
            source = str(values[f"{kind}_source"])
            if source == "base":
                if kind == "persona":
                    with self.database.connect() as connection:
                        found = connection.execute("SELECT 1 FROM base_personas WHERE id = ?", (item_id,)).fetchone()
                    if found is None:
                        raise NotFoundError(f"{kind}_not_found")
                    continue
                if item_id not in base_items:
                    raise NotFoundError(f"{kind}_not_found")
                continue
            with self.database.connect() as connection:
                found = connection.execute(
                    "SELECT 1 FROM custom_items WHERE kind = ? AND id = ?",
                    (kind, item_id),
                ).fetchone()
            if found is None:
                raise NotFoundError(f"{kind}_not_found")

    def end_target(self, target_id: str) -> dict[str, Any]:
        now = utc_now()
        with self.database.connect() as connection:
            cursor = connection.execute(
                "UPDATE targets SET status = 'ended', reply_enabled = 0, ended_at = ?, updated_at = ? WHERE id = ?",
                (now, now, target_id),
            )
            if cursor.rowcount == 0:
                raise NotFoundError("target_not_found")
        return self.get_target(target_id)

    def revive_target(self, target_id: str) -> dict[str, Any]:
        with self.database.connect() as connection:
            cursor = connection.execute(
                "UPDATE targets SET status = 'active', reply_enabled = 0, ended_at = NULL, updated_at = ? WHERE id = ?",
                (utc_now(), target_id),
            )
            if cursor.rowcount == 0:
                raise NotFoundError("target_not_found")
        return self.get_target(target_id)

    def delete_target(self, target_id: str) -> None:
        with self.database.connect() as connection:
            cursor = connection.execute("DELETE FROM targets WHERE id = ?", (target_id,))
            if cursor.rowcount == 0:
                raise NotFoundError("target_not_found")

    def save_custom_item(self, kind: str, values: dict[str, Any], item_id: str | None = None) -> dict[str, Any]:
        item_id = item_id or f"custom-{kind}-{uuid.uuid4().hex}"
        now = utc_now()
        name = str(values.get("name", "")).strip()
        try:
            with self.database.connect() as connection:
                existing = connection.execute("SELECT created_at FROM custom_items WHERE id = ?", (item_id,)).fetchone()
                created_at = existing["created_at"] if existing else now
                connection.execute(
                    """
                    INSERT INTO custom_items(id, kind, name, name_key, text, image_data_url, source_base_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET name = excluded.name, name_key = excluded.name_key,
                        text = excluded.text, image_data_url = excluded.image_data_url,
                        source_base_id = excluded.source_base_id, updated_at = excluded.updated_at
                    """,
                    (
                        item_id, kind, name, normalized_name(name), str(values.get("text", "")).strip(),
                        values.get("image_data_url"), values.get("source_base_id"), created_at, now,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ConflictError("duplicate_custom_name") from exc
        return self.get_custom_item(kind, item_id)

    def get_custom_item(self, kind: str, item_id: str) -> dict[str, Any]:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM custom_items WHERE kind = ? AND id = ?", (kind, item_id)).fetchone()
        result = _row(row)
        if result is None:
            raise NotFoundError("custom_item_not_found")
        return result

    def list_custom_items(self, kind: str) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM custom_items WHERE kind = ? ORDER BY created_at, id", (kind,)
            ).fetchall()
        return [_row(row) for row in rows]  # type: ignore[misc]

    def delete_custom_item(self, kind: str, item_id: str) -> None:
        column = "persona_id" if kind == "persona" else "weapon_id"
        source_column = "persona_source" if kind == "persona" else "weapon_source"
        with self.database.connect() as connection:
            used = connection.execute(
                f"SELECT 1 FROM targets WHERE {column} = ? AND {source_column} = 'custom' LIMIT 1",
                (item_id,),
            ).fetchone()
            if used:
                raise ConflictError("custom_item_in_use")
            cursor = connection.execute("DELETE FROM custom_items WHERE kind = ? AND id = ?", (kind, item_id))
            if cursor.rowcount == 0:
                raise NotFoundError("custom_item_not_found")

    def add_message(self, target_id: str, role: str, content: str, created_at: str | None = None) -> dict[str, Any]:
        created_at = created_at or utc_now()
        with self.database.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO messages(target_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (target_id, role, content, created_at),
            )
            if role == "assistant":
                connection.execute(
                    """
                    UPDATE targets SET round_trips = round_trips + 1,
                        first_reply_at = COALESCE(first_reply_at, ?), last_reply_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (created_at, created_at, utc_now(), target_id),
                )
            row = connection.execute("SELECT * FROM messages WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)

    def record_exchange(self, target_id: str, incoming: str, reply: str) -> None:
        created_at = utc_now()
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO messages(target_id, role, content, created_at) VALUES (?, 'scammer', ?, ?)",
                (target_id, incoming, created_at),
            )
            connection.execute(
                "INSERT INTO messages(target_id, role, content, created_at) VALUES (?, 'assistant', ?, ?)",
                (target_id, reply, created_at),
            )
            cursor = connection.execute(
                """
                UPDATE targets SET round_trips = round_trips + 1,
                    first_reply_at = COALESCE(first_reply_at, ?), last_reply_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (created_at, created_at, created_at, target_id),
            )
            if cursor.rowcount == 0:
                raise NotFoundError("target_not_found")

    def list_messages(self, target_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            if limit is None:
                rows = connection.execute(
                    "SELECT * FROM messages WHERE target_id = ? ORDER BY created_at, id", (target_id,)
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM (
                        SELECT * FROM messages WHERE target_id = ? ORDER BY created_at DESC, id DESC LIMIT ?
                    ) ORDER BY created_at, id
                    """,
                    (target_id, limit),
                ).fetchall()
        return [dict(row) for row in rows]

    def dashboard_metrics(self) -> dict[str, int]:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS target_count,
                       COALESCE(SUM(round_trips), 0) AS total_round_trips,
                       COALESCE(SUM(CASE WHEN first_reply_at IS NOT NULL AND last_reply_at IS NOT NULL
                           THEN (julianday(last_reply_at) - julianday(first_reply_at)) * 86400000 ELSE 0 END), 0) AS total_duration_ms,
                       COALESCE(SUM(CASE WHEN status = 'ended' THEN 1 ELSE 0 END), 0) AS ended_count
                FROM targets
                """
            ).fetchone()
        return {
            "target_count": int(row["target_count"]),
            "total_round_trips": int(row["total_round_trips"]),
            "total_duration_ms": round(float(row["total_duration_ms"])),
            "ended_count": int(row["ended_count"]),
        }
