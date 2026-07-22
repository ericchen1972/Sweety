from __future__ import annotations

from sweety_app.catalog import DEFAULT_SYSTEM_PROMPT_TEMPLATE
from sweety_app.database import Database
from sweety_app.repositories import Repository


def _schema_version(database: Database) -> int:
    with database.connect() as connection:
        return int(connection.execute("SELECT version FROM schema_version").fetchone()["version"])


def test_v1_database_upgrades_its_bundled_system_prompt_to_current_schema(tmp_path):
    database = Database(tmp_path / "sweety.sqlite3")
    database.migrate()
    with database.connect() as connection:
        connection.execute("UPDATE schema_version SET version = 1")
        connection.execute(
            "UPDATE system_prompts SET template = ?, updated_at = datetime('now') WHERE singleton = 1",
            ("舊版內建 prompt，還沒有人設知識邊界",),
        )

    database.migrate()

    assert _schema_version(database) == 4
    assert Repository(database).get_system_prompt_template() == DEFAULT_SYSTEM_PROMPT_TEMPLATE


def test_v2_migration_does_not_replace_a_later_cached_remote_prompt(tmp_path):
    database = Database(tmp_path / "sweety.sqlite3")
    database.migrate()
    repository = Repository(database)
    remote_prompt = "遠端自訂 prompt {persona_text} {total_messages}"
    repository.replace_remote_catalog(system_prompt_template=remote_prompt, base_personas=[])

    database.migrate()

    assert _schema_version(database) == 4
    assert repository.get_system_prompt_template() == remote_prompt


def test_v2_database_upgrades_to_v3_without_replacing_remote_prompt(tmp_path):
    database = Database(tmp_path / "sweety.sqlite3")
    database.migrate()
    repository = Repository(database)
    remote_prompt = "已從遠端同步的 prompt {persona_text} {total_messages}"
    repository.replace_remote_catalog(system_prompt_template=remote_prompt, base_personas=[])
    with database.connect() as connection:
        connection.execute("UPDATE schema_version SET version = 2")

    database.migrate()

    assert _schema_version(database) == 4
    assert repository.get_system_prompt_template() == remote_prompt
    with database.connect() as connection:
        columns = connection.execute("PRAGMA table_info(app_metadata)").fetchall()
    assert [row["name"] for row in columns] == ["key", "value"]


def test_v3_persona_table_migrates_to_canonical_content_columns(tmp_path):
    database = Database(tmp_path / "legacy.sqlite3")
    database.migrate()
    with database.connect() as connection:
        connection.execute("UPDATE schema_version SET version = 3")
        connection.execute("ALTER TABLE base_personas RENAME TO base_personas_v4_seed")
        connection.execute(
            """
            CREATE TABLE base_personas (
                id TEXT PRIMARY KEY, age_group TEXT NOT NULL, gender TEXT NOT NULL,
                name_zh_tw TEXT NOT NULL, name_en TEXT NOT NULL,
                summary_zh_tw TEXT NOT NULL, summary_en TEXT NOT NULL,
                profile_zh_tw TEXT NOT NULL, profile_en TEXT NOT NULL,
                style_zh_tw TEXT NOT NULL, style_en TEXT NOT NULL,
                text_zh_tw TEXT NOT NULL, text_en TEXT NOT NULL,
                image TEXT NOT NULL, sort_order INTEGER NOT NULL, updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute("DROP TABLE base_personas_v4_seed")
        connection.execute(
            """
            INSERT INTO base_personas VALUES (
                'legacy-persona', '65+', 'female', '舊人設', 'Legacy Persona',
                '摘要', 'Summary', '人物資料', 'Profile', '風格個性', 'Style',
                '人物資料：\n完整舊人設', 'Character information:\nComplete legacy persona',
                '/legacy.jpg', 1, '2026-07-22T00:00:00Z'
            )
            """
        )

    database.migrate()

    assert _schema_version(database) == 4
    with database.connect() as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(base_personas)")}
        migrated = connection.execute("SELECT * FROM base_personas WHERE id = 'legacy-persona'").fetchone()
    assert columns == {
        "id", "age_group", "gender", "name_zh_tw", "name_en",
        "content_zh_tw", "content_en", "image", "sort_order", "updated_at",
    }
    assert migrated["content_zh_tw"] == "人物資料：\n完整舊人設"
