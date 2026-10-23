"""Durable account-scoped LINE request numbers, committed before network I/O."""
import hashlib
from pathlib import Path
import sqlite3
import time


def next_sequence(directory, mid, *, now=None):
    if not mid:
        raise ValueError('line_request_sequence_account_missing')
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    path=directory/'request-sequences.sqlite3'
    key=hashlib.sha256(mid.encode()).hexdigest()
    with sqlite3.connect(path,timeout=30) as db:
        db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE IF NOT EXISTS request_sequences(account TEXT PRIMARY KEY,value INTEGER NOT NULL)')
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT value FROM request_sequences WHERE account=?',(key,)).fetchone()
        # Epoch seconds avoid the old SDK's low counter values on migration.
        value=max(int(time.time() if now is None else now),row[0] if row else 0)+1
        if value>2147483647:
            raise ValueError('line_request_sequence_exhausted')
        db.execute('INSERT INTO request_sequences VALUES(?,?) ON CONFLICT(account) DO UPDATE SET value=excluded.value',(key,value))
    path.chmod(0o600)
    return value
