import json
import pytest
from fastapi.testclient import TestClient
from sweety_app.api import create_app
from sweety_app.database import Database
from sweety_app.repositories import Repository
from test_repositories import target_payload
from test_okline import ready, incoming


def make_repo(tmp_path):
    db = Database(tmp_path / 'context.sqlite3'); db.migrate()
    return db, Repository(db)


def test_context_default_and_api_boundaries(tmp_path):
    db, repo = make_repo(tmp_path)
    assert repo.get_settings()['history_limit'] == 6
    client = TestClient(create_app(db))
    for value in (3, 31):
        state = client.get('/api/state').json()
        state['settings']['historyLimit'] = value
        assert client.put('/api/state', json=state).status_code == 422
    for value in (4, 6, 30):
        state = client.get('/api/state').json()
        state['settings']['historyLimit'] = value
        assert client.put('/api/state', json=state).status_code == 200


def test_conversation_export_removed(tmp_path):
    db,repo = make_repo(tmp_path)
    t = repo.create_target(target_payload())
    client=TestClient(create_app(db))
    assert client.get(f"/api/targets/{t['id']}/export").status_code == 404


def test_stopping_discards_ram_pending_work_without_storing_content(tmp_path):
    repo,store,service,t,monitor,calls=ready(tmp_path)
    for i in range(15):store.ingest(incoming(f'stop-{i}',text=f'secret-{i}'))
    monitor.stop()
    assert store.rows()==[] and store._payloads=={}
    with repo.database.connect() as c:
        assert c.execute('SELECT COUNT(*) FROM messages').fetchone()[0]==0
        assert c.execute("SELECT COUNT(*) FROM line_inbox WHERE raw!='{}'").fetchone()[0]==0
    assert repo.get_target(t['id'])['round_trips']==0
