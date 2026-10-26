"""Bounded AI context, not a conversation archive."""
DEFAULT_HISTORY_LIMIT = 6
MIN_HISTORY_LIMIT = 4
MAX_HISTORY_LIMIT = 30


def prune_context(connection):
    limit = connection.execute('SELECT history_limit FROM settings WHERE singleton=1').fetchone()[0]
    has_inbox = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='line_inbox'").fetchone()
    protected = "SELECT incoming_id FROM line_inbox WHERE status IN ('pending','processing','sending','context') AND incoming_id IS NOT NULL" if has_inbox else 'SELECT NULL WHERE 0'
    # Unresolved inputs are temporary delivery work, not historical context.
    connection.execute(f"""DELETE FROM messages WHERE id IN (
        SELECT id FROM (SELECT id,ROW_NUMBER() OVER (
            PARTITION BY target_id ORDER BY julianday(created_at) DESC,id DESC) AS position
            FROM messages WHERE id NOT IN ({protected})) WHERE position > ?
        )""", (limit,))
    if has_inbox:
        connection.execute("UPDATE line_inbox SET raw='{}' WHERE status IN ('sent','archived','failed','uncertain') AND raw!='{}'")
