import threading
import time
from types import SimpleNamespace
from test_okline import setup, assignment, incoming


def test_history_pagination_uses_sdk_delivered_time_and_deduplicates(tmp_path):
    repo,store,service=setup(tmp_path);t=store.add('u1',assignment());repo.update_target(t['id'],{'reply_enabled':True})
    now=int(time.time()*1000)+1000
    service.receive_cutoff=(now-500)/1000;store.since=now-500;service.allow_receiving=lambda:True
    page_calls=[]
    service.api.get_recent_messages=lambda *a:[incoming('new',createdTime=now,deliveredTime=now+20)]
    def previous(box,end_message_id,delivered_time,count=100):
        page_calls.append((box,end_message_id,delivered_time,count))
        return [incoming('new',createdTime=now),incoming('old',createdTime=now-1000)]
    service.api.get_previous_messages=previous
    service.reconcile_history(threading.Event());service.reconcile_history(threading.Event())
    assert page_calls[0]==('u1','new',now+20,50)
    assert len(store.rows())==1


def test_cancelled_qr_login_cannot_reactivate_account(tmp_path):
    repo,store,service=setup(tmp_path)
    class Client:
        tokens=SimpleNamespace(mid='self')
        def get_profile(self):return {'mid':'self','displayName':'Test'}
    generation=service.generation
    service.disconnect()
    import pytest
    with pytest.raises(ValueError,match='cancelled'):service._accept(Client(),generation)
    assert not service.connected() and not store.scope


def test_stream_reconnect_keeps_failed_decrypt_revision_unadvanced(tmp_path,monkeypatch):
    repo,store,service=setup(tmp_path);t=store.add('u1',assignment());repo.update_target(t['id'],{'reply_enabled':True})
    store.advance(10);service.allow_receiving=lambda:True
    service.api.decrypt_message=lambda m:(_ for _ in ()).throw(ValueError('decrypt failed'))
    import pytest
    with pytest.raises(ValueError):service.ingest(incoming('encrypted',chunks=['a']),11)
    assert store.cursor()==10


def test_direct_send_cannot_cross_accounts_or_blocked_contact(tmp_path):
    repo,store,service=setup(tmp_path);t=store.add('u1',assignment());repo.update_target(t['id'],{'reply_enabled':True})
    import pytest
    with pytest.raises(Exception):service.send(t['id'],'text',expected_scope='another')
    store.refresh_contacts([])
    with pytest.raises(Exception):service.send(t['id'],'text')
