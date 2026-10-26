import json
import pytest
from test_okline import ready, incoming


def message(mid,stamp,*,sender='u1',text='old',**kw):
    return {'id':mid,'from':sender,'to':'self' if sender=='u1' else 'u1','createdTime':stamp,'contentType':0,'text':text,**kw}


def test_live_history_is_decrypted_ordered_and_excludes_queued_or_future(tmp_path):
    repo,store,line,t,monitor,calls=ready(tmp_path)
    pages=[message('new',100,text='current'),message('old2',20,sender='self',text='answer'),message('future',101),message('old1',10,text='question')]
    line.api.get_recent_messages=lambda *a:pages
    result=line.history_for_reply(t['id'],4,exclude_ids={'new'},before=100)
    assert result==[{'role':'scammer','content':'question'},{'role':'assistant','content':'answer'}]
    line.api.get_recent_messages=lambda *a:[message('encrypted',5,chunks=['secret'])]
    line.api.decrypt_message=lambda m:{**m,'text':'decrypted','chunks':None}
    assert line.history_for_reply(t['id'],4,exclude_ids=set(),before=100)[0]['content']=='decrypted'
    monitor.stop()


def test_history_paginates_to_requested_limit(tmp_path):
    repo,store,line,t,monitor,calls=ready(tmp_path)
    line.api.get_recent_messages=lambda *a:[message('new',100),message('a',90)]
    line.api.get_previous_messages=lambda *a,**kw:[message(str(i),i) for i in range(80,86)]
    result=line.history_for_reply(t['id'],4,exclude_ids={'new'},before=100)
    assert len(result)==4 and [m['content'] for m in result]==['old']*4
    monitor.stop()


def test_history_failure_never_calls_ai_or_sends(tmp_path):
    repo,store,line,t,monitor,calls=ready(tmp_path)
    line.api.get_recent_messages=lambda *a:(_ for _ in ()).throw(TimeoutError('offline'))
    sent=[];line.api.send_text=lambda *a:sent.append(a)
    store.ingest(incoming('current',text='sensitive incoming'))
    assert not monitor.run_cycle()
    assert not calls and not sent
    assert monitor.snapshot()['message']=='LINE 交談歷史讀取失敗，本次未回覆。'
    monitor.stop()


def test_pending_and_completed_content_never_written_to_sqlite(tmp_path):
    repo,store,line,t,monitor,calls=ready(tmp_path)
    line.api.get_recent_messages=lambda *a:[]
    store.ingest(incoming('current',text='sensitive incoming'))
    def assert_clean():
        with repo.database.connect() as c:
            assert c.execute('SELECT COUNT(*) FROM messages').fetchone()[0]==0
            assert c.execute("SELECT COUNT(*) FROM line_inbox WHERE raw!='{}'").fetchone()[0]==0
        assert b'sensitive incoming' not in repo.database.path.read_bytes()
    assert_clean()
    assert monitor.run_cycle()
    assert_clean()
    assert repo.get_target(t['id'])['round_trips']==1
    assert store.row('current')['status']=='sent'
    assert store.rows()==[]
    monitor.stop()


def test_history_cancelled_mid_fetch_never_calls_ai(tmp_path):
    repo,store,line,t,monitor,calls=ready(tmp_path)
    def cancel(*a):
        monitor.stop();return []
    line.api.get_recent_messages=cancel
    store.ingest(incoming('current'))
    assert not monitor.run_cycle() and calls==[]


def test_legacy_all_content_is_cleared_on_upgrade(tmp_path):
    from sweety_app.database import Database
    from sweety_app.repositories import Repository
    from test_repositories import target_payload
    db=Database(tmp_path/'legacy.sqlite3');db.migrate();repo=Repository(db)
    t=repo.create_target(target_payload())
    with db.connect() as c:
        c.execute("INSERT INTO messages(target_id,role,content,created_at) VALUES(?,'scammer','legacy secret','2026-01-01')",(t['id'],))
        c.execute('UPDATE schema_version SET version=12')
    db.migrate()
    with db.connect() as c:assert c.execute('SELECT COUNT(*) FROM messages').fetchone()[0]==0


def test_switching_account_discards_pending_payloads(tmp_path):
    repo,store,line,t,monitor,calls=ready(tmp_path)
    store.ingest(incoming('switch',text='private pending'))
    store.activate('other-account')
    assert store._payloads=={}
    monitor.stop()


@pytest.mark.parametrize('payload', [[{'createdTime':10,'text':'missing id'}],[None],{'messages':[{'id':'old'}]}])
def test_malformed_history_fails_closed(tmp_path,payload):
    repo,store,line,t,monitor,calls=ready(tmp_path)
    line.api.get_recent_messages=lambda *a:payload
    store.ingest(incoming('current'))
    assert not monitor.run_cycle()
    assert calls==[] and repo.get_target(t['id'])['round_trips']==0
    monitor.stop()
