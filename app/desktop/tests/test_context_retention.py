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


def test_context_is_bounded_without_losing_statistics(tmp_path):
    db, repo = make_repo(tmp_path)
    t = repo.create_target(target_payload())
    for i in range(12): repo.record_exchange(t['id'], f'in-{i}', f'out-{i}')
    assert [m['content'] for m in repo.list_messages(t['id'])] == ['in-9','out-9','in-10','out-10','in-11','out-11']
    assert repo.get_target(t['id'])['round_trips'] == 12
    repo.update_settings({'history_limit':4})
    assert len(repo.list_messages(t['id'])) == 4


def test_startup_trims_legacy_records_and_old_default(tmp_path):
    db, repo = make_repo(tmp_path)
    t = repo.create_target(target_payload())
    with db.connect() as c:
        c.execute('UPDATE schema_version SET version=11')
        c.execute('UPDATE settings SET history_limit=20')
        for i in range(40): c.execute("INSERT INTO messages(target_id,role,content,created_at) VALUES(?,'scammer',?,?)",(t['id'],str(i),f'{i:03}'))
    db.migrate()
    repo = Repository(db)
    assert repo.get_settings()['history_limit'] == 6
    assert [m['content'] for m in repo.list_messages(t['id'])] == list(map(str,range(34,40)))


def test_finished_journal_has_no_transcript_but_dedup_survives(tmp_path):
    repo,store,service,t,monitor,calls = ready(tmp_path)
    store.ingest(incoming('private-message', text='private incoming'))
    assert monitor.run_cycle()
    assert json.loads(store.row('private-message')['raw']) == {}
    assert store.row('private-message')['status'] == 'sent'
    assert not store.ingest(incoming('private-message'))
    assert len(repo.list_messages(t['id'])) == 2
    monitor.stop()


def test_queued_input_survives_retention_and_eventually_scrubs(tmp_path):
    repo,store,service,t,monitor,calls = ready(tmp_path)
    for i in range(11): store.ingest(incoming(f'queued-{i}',text=f'input-{i}'))
    receipts=iter(['r1','r2'])
    service.api.send_text=lambda *args:{'id':next(receipts)}
    assert monitor.run_cycle()
    assert json.loads(store.row('queued-10')['raw'])['text'] == 'input-10'
    assert monitor.run_cycle()
    assert len(calls) == 2
    assert len(calls[1]['incoming_messages']) == 3
    assert len(repo.list_messages(t['id'])) <= 6
    assert json.loads(store.row('queued-10')['raw']) == {}
    monitor.stop()


def test_conversation_export_removed(tmp_path):
    db,repo = make_repo(tmp_path)
    t = repo.create_target(target_payload())
    client=TestClient(create_app(db))
    assert client.get(f"/api/targets/{t['id']}/export").status_code == 404


def test_stopping_finalizes_unprocessed_context(tmp_path):
    repo,store,service,t,monitor,calls = ready(tmp_path)
    for i in range(15): store.ingest(incoming(f'stop-{i}',text=f'secret-{i}'))
    monitor.stop()
    assert len(repo.list_messages(t['id'])) == 6
    with repo.database.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM line_inbox WHERE raw!='{}'").fetchone()[0] == 0
    assert repo.get_target(t['id'])['round_trips'] == 0


def test_startup_finalizes_crashed_pending_work(tmp_path):
    from sweety_app.okline_store import LineStore
    repo,store,service,t,monitor,calls = ready(tmp_path)
    for i in range(15): store.ingest(incoming(f'crash-{i}'))
    # Simulate a process restart before a monitor cycle or clean stop.
    replacement=LineStore(repo)
    assert len(repo.list_messages(t['id'])) == 6
    with repo.database.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM line_inbox WHERE raw!='{}'").fetchone()[0] == 0
    monitor.stop()


def test_prune_failure_releases_cycle_lock(tmp_path):
    repo,store,service,t,monitor,calls = ready(tmp_path)
    original=repo.prune_context
    repo.prune_context=lambda:(_ for _ in ()).throw(RuntimeError('disk failure'))
    with pytest.raises(RuntimeError): monitor.run_cycle()
    assert monitor._cycle_lock.acquire(blocking=False)
    monitor._cycle_lock.release()
    repo.prune_context=original
    monitor.stop()
