"""AI context limits and removal of legacy on-disk transcripts."""
DEFAULT_HISTORY_LIMIT = 6
MIN_HISTORY_LIMIT = 4
MAX_HISTORY_LIMIT = 30


def purge_legacy_content(connection):
    connection.execute('DELETE FROM messages')
    if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='line_inbox'").fetchone():
        connection.execute("UPDATE line_inbox SET raw='{}',incoming_id=NULL WHERE raw!='{}' OR incoming_id IS NOT NULL")
