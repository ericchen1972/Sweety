from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .catalog import BASE_PERSONAS, DEFAULT_SYSTEM_PROMPT_TEMPLATE


CURRENT_SCHEMA_VERSION = 4


SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    ai_provider TEXT NOT NULL,
    openai_api_key TEXT NOT NULL,
    openai_model TEXT NOT NULL,
    check_interval_seconds INTEGER NOT NULL,
    reply_delay_min_seconds INTEGER NOT NULL,
    reply_delay_max_seconds INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS system_prompts (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    template TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS base_personas (
    id TEXT PRIMARY KEY,
    age_group TEXT NOT NULL DEFAULT '20-35',
    gender TEXT NOT NULL,
    name_zh_tw TEXT NOT NULL,
    name_en TEXT NOT NULL,
    content_zh_tw TEXT NOT NULL,
    content_en TEXT NOT NULL,
    image TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS custom_items (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('persona', 'weapon')),
    name TEXT NOT NULL,
    name_key TEXT NOT NULL,
    text TEXT NOT NULL,
    image_data_url TEXT,
    source_base_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(kind, name_key)
);

CREATE TABLE IF NOT EXISTS targets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    name_key TEXT NOT NULL UNIQUE,
    age_group TEXT NOT NULL,
    gender TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    persona_source TEXT NOT NULL,
    weapon_id TEXT NOT NULL,
    weapon_source TEXT NOT NULL,
    reply_enabled INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    round_trips INTEGER NOT NULL DEFAULT 0,
    first_reply_at TEXT,
    last_reply_at TEXT,
    ended_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id TEXT NOT NULL REFERENCES targets(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('scammer', 'assistant')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_targets_monitor
ON targets(status, reply_enabled);

CREATE INDEX IF NOT EXISTS idx_messages_target_created
ON messages(target_id, created_at, id);
"""


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._local = threading.local()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        existing = getattr(self._local, "connection", None)
        if existing is not None:
            yield existing
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        self._local.connection = connection
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            self._local.connection = None
            connection.close()

    def migrate(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            version_row = connection.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            if version_row is None:
                previous_version = CURRENT_SCHEMA_VERSION
                connection.execute(
                    "INSERT INTO schema_version(version) VALUES (?)",
                    (CURRENT_SCHEMA_VERSION,),
                )
            else:
                previous_version = int(version_row["version"])
                if previous_version < 2:
                    connection.execute(
                        """
                        UPDATE system_prompts
                        SET template = ?, updated_at = datetime('now')
                        WHERE singleton = 1
                        """,
                        (DEFAULT_SYSTEM_PROMPT_TEMPLATE,),
                    )
            connection.execute(
                """
                INSERT OR IGNORE INTO settings(
                    singleton, ai_provider, openai_api_key, openai_model,
                    check_interval_seconds, reply_delay_min_seconds,
                    reply_delay_max_seconds
                ) VALUES (1, 'sweety', '', 'gpt-5.5', 10, 15, 45)
                """
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO system_prompts(singleton, template, updated_at)
                VALUES (1, ?, datetime('now'))
                """,
                (DEFAULT_SYSTEM_PROMPT_TEMPLATE,),
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(base_personas)").fetchall()
            }
            if "age_group" not in columns:
                connection.execute("ALTER TABLE base_personas ADD COLUMN age_group TEXT NOT NULL DEFAULT '20-35'")
                columns.add("age_group")
            if "content_zh_tw" not in columns or {
                "summary_zh_tw", "profile_zh_tw", "style_zh_tw", "text_zh_tw"
            } & columns:
                zh_source = "text_zh_tw" if "text_zh_tw" in columns else "profile_zh_tw"
                en_source = "text_en" if "text_en" in columns else "profile_en"
                connection.execute("DROP TABLE IF EXISTS base_personas_v4")
                connection.execute(
                    """
                    CREATE TABLE base_personas_v4 (
                        id TEXT PRIMARY KEY,
                        age_group TEXT NOT NULL DEFAULT '20-35',
                        gender TEXT NOT NULL,
                        name_zh_tw TEXT NOT NULL,
                        name_en TEXT NOT NULL,
                        content_zh_tw TEXT NOT NULL,
                        content_en TEXT NOT NULL,
                        image TEXT NOT NULL,
                        sort_order INTEGER NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    f"""
                    INSERT INTO base_personas_v4(
                        id, age_group, gender, name_zh_tw, name_en,
                        content_zh_tw, content_en, image, sort_order, updated_at
                    )
                    SELECT id, age_group, gender, name_zh_tw, name_en,
                           {zh_source}, {en_source}, image, sort_order, updated_at
                    FROM base_personas
                    """
                )
                connection.execute("DROP TABLE base_personas")
                connection.execute("ALTER TABLE base_personas_v4 RENAME TO base_personas")
            for index, persona in enumerate(BASE_PERSONAS):
                connection.execute(
                    """
                    INSERT OR IGNORE INTO base_personas(
                        id, age_group, gender, name_zh_tw, name_en,
                        content_zh_tw, content_en, image, sort_order, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        persona["id"], persona.get("ageGroup", "20-35"), persona["gender"],
                        persona["name"]["zh-TW"], persona["name"]["en"],
                        persona["content"]["zh-TW"], persona["content"]["en"],
                        persona["image"], index,
                    ),
                )
            if previous_version < CURRENT_SCHEMA_VERSION:
                connection.execute(
                    "UPDATE schema_version SET version = ?",
                    (CURRENT_SCHEMA_VERSION,),
                )
