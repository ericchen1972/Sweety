import time
from threading import Event
from types import SimpleNamespace
import pytest
from sweety_app.database import Database
from sweety_app.repositories import Repository
from sweety_app.ai import ReplyDecision


def setup(tmp_path):
    from sweety_app.okline_store import LineStore
    from sweety_app.okline_service import LineService
    db=Database(tmp_path/'test.sqlite3'); db.migrate()
    repo=Repository(db); repo.update_settings({"agnes_api_key":"test-key"}); store=LineStore(repo); store.activate('self')
    store.refresh_contacts([{'id':'u1','name':'同名 😊','blocked':False}, {'id':'u2','name':'同名 😊','blocked':False}, {'id':'u3','name':'封鎖','blocked':True}])
    service=LineService(repo,store)
    service.state={'status':'connected'}
    service.api=SimpleNamespace(send_text=lambda mid,text:{'id':'receipt'},mark_as_read=lambda *a:None)
    # A fake remote LINE server keeps history separately from the local journal.
    service.api.history=[]
    service.api.get_recent_messages=lambda mid,count:service.api.history[-count:]
    service.api.get_previous_messages=lambda *a,**kw:[]
    original_ingest=store.ingest
    def remote_ingest(message,*a,**kw):
        service.api.history.append(dict(message))
        return original_ingest(message,*a,**kw)
    store.ingest=remote_ingest
    return repo,store,service


def assignment(name='Old'):
    return dict(name=name,age_group='20-35',gender='female',persona_id='cautious-accounting-assistant',persona_source='base',weapon_id='one-step-at-a-time',weapon_source='base',reply_enabled=True)


def test_binding_retains_everything_and_same_names_are_distinct(tmp_path):
    repo,store,service=setup(tmp_path)
    old=repo.create_target(assignment()); repo.record_reply(old['id'])
    before=repo.get_target(old['id'])
    bound=store.bind(old['id'],'u1')
    assert bound['id']==old['id'] and bound['weapon_id']==before['weapon_id']
    assert bound['round_trips']==1
    other=store.add('u2',assignment())
    assert other['name']==bound['name'] and other['id']!=bound['id']
    with pytest.raises(ValueError):store.bind(other['id'],'u1')
    with pytest.raises(ValueError):store.add('u3',assignment())
    store.activate('different-account')
    assert store.targets()==[] and store.contacts()==[]


def test_unbound_targets_never_receive_or_enable_by_name(tmp_path):
    repo,store,service=setup(tmp_path)
    repo.create_target(assignment('同名 😊'))
    assert store.targets()==[]
    assert not store.ingest({'id':'m1','from':'u1','to':'self','text':'hello','createdTime':int(time.time()*1000)})


def ready(tmp_path):
    from sweety_app.monitor import MonitorController
    repo,store,service=setup(tmp_path); t=store.add('u1',assignment());repo.update_target(t['id'],{'reply_enabled':True})
    calls=[]
    class AI:
        def generate_reply(self,**kw):
            calls.append(kw);return ReplyDecision(incoming_summary='incoming',msg_reply='reply')
    monitor=MonitorController(repo,service,AI(),sleeper=lambda _:None)
    # Fake network receiver still exercises the real journal and worker.
    service.start_receiving=lambda:None
    assert monitor.start(background=False)
    return repo,store,service,t,monitor,calls


def incoming(mid,text='hello',**kw):
    return {'id':mid,'from':'u1','to':'self','text':text,'contentType':0,'createdTime':int(time.time()*1000)+10,**kw}


def test_text_without_desktop_audio_and_deduplicated_confirmed_stats(tmp_path):
    repo,store,service,t,monitor,calls=ready(tmp_path)
    assert store.ingest(incoming('m1'))
    assert not store.ingest(incoming('m1'))
    assert monitor.run_cycle()
    assert len(calls)==1 and 'screenshot_path' not in calls[0]
    assert calls[0]['incoming_messages'][0]['text']=='hello'
    assert repo.get_target(t['id'])['round_trips']==1
    assert not monitor.run_cycle()
    monitor.stop()


def test_manual_outgoing_is_context_only(tmp_path):
    repo,store,service,t,monitor,calls=ready(tmp_path)
    store.ingest(incoming('own',text='manual',**{'from':'self','to':'u1','createdTime':int(time.time()*1000)-1000}))
    monitor.run_cycle(); assert calls==[]
    assert repo.get_target(t['id'])['round_trips']==0
    store.ingest(incoming('text'))
    monitor.run_cycle(); assert len(calls)==1
    assert any(x['content']=='manual' and x['role']=='assistant' for x in calls[0]['history'])


@pytest.mark.parametrize(('read_fails', 'ai_seconds'), [(False, 1), (True, 9)])
def test_reply_waits_to_read_and_type(tmp_path, monkeypatch, read_fails, ai_seconds):
    from sweety_app import monitor as monitor_module, okline_store

    repo, store, service, target, monitor, calls = ready(tmp_path)
    repo.update_settings({'reply_delay_min_seconds': 6, 'reply_delay_max_seconds': 8})
    events = []
    now = 100.0
    clock = SimpleNamespace(time=time.time, sleep=time.sleep, monotonic=lambda: now)
    monkeypatch.setattr(monitor_module, 'time', clock)
    monkeypatch.setattr(okline_store, 'time', clock)
    draws = []

    def uniform(low, high):
        draws.append((low, high))
        return 5 if low == 3 else 7

    monkeypatch.setattr(monitor_module.random, 'uniform', uniform)
    first = incoming('100')
    latest = incoming('101', createdTime=first['createdTime'] + 1)

    def sleep(seconds):
        nonlocal now
        now += seconds
        if not events:
            assert store.ingest(latest)
        events.append(('wait', seconds))

    def send(mid, text):
        events.append(('send', mid, text))
        return {'id': 'receipt'}

    def mark_as_read(mid, message_id):
        events.append(('read', mid, message_id))
        if read_fails:
            raise TimeoutError('read receipt unavailable')

    service.api.send_text = send
    service.api.mark_as_read = mark_as_read
    monitor.sleeper = sleep
    generate = monitor.ai.generate_reply

    def generate_reply(**kwargs):
        nonlocal now
        events.append(('ai',))
        now += ai_seconds
        return generate(**kwargs)

    monitor.ai.generate_reply = generate_reply
    assert store.ingest(first)
    now += 2  # The worker picked up the batch two seconds after receipt.

    assert monitor.run_cycle()
    assert not monitor.run_cycle()
    assert draws == [(3, 10), (6, 8)]
    expected = [('wait', 3), ('read', 'u1', '101'), ('ai',)]
    if ai_seconds < 7:
        expected.append(('wait', 7 - ai_seconds))
    assert events == expected + [('send', 'u1', 'reply')]
    assert [message['id'] for message in calls[0]['incoming_messages']] == ['100', '101']
    assert repo.get_target(target['id'])['round_trips'] == 1


def test_read_watermark_stays_within_processed_batch(tmp_path):
    _, store, service, _, monitor, _ = ready(tmp_path)
    checked = []
    service.api.mark_as_read = lambda mid, message_id: checked.append(message_id)
    stamp = incoming('107')['createdTime']
    for message_id in range(107, 98, -1):
        assert store.ingest(incoming(str(message_id), createdTime=stamp))

    assert monitor.run_cycle()
    assert store.row('107')['status'] == 'pending'
    assert checked == ['106']
    assert monitor.run_cycle()
    assert checked == ['106', '107']


def test_stop_during_ai_never_sends_or_replays(tmp_path):
    repo,store,service,t,monitor,calls=ready(tmp_path)
    sent=[];service.api.send_text=lambda *a:sent.append(a)
    def stop_ai(**kw):
        monitor.stop();return ReplyDecision(incoming_summary='hello',msg_reply='reply')
    monitor.ai.generate_reply=stop_ai
    store.ingest(incoming('m1'));monitor.run_cycle()
    assert sent==[] and repo.get_target(t['id'])['round_trips']==0
    assert monitor.start(background=False)
    assert not monitor.run_cycle()
    assert sent==[]


def test_uncertain_send_is_not_retried_or_counted(tmp_path):
    repo,store,service,t,monitor,calls=ready(tmp_path)
    sent=[]
    def uncertain(*args):sent.append(args);raise TimeoutError('unknown')
    service.api.send_text=uncertain
    reads=[]
    service.api.mark_as_read=lambda *args: reads.append(args)
    store.ingest(incoming('m1'));monitor.run_cycle();monitor.run_cycle()
    assert reads == [('u1', 'm1')]
    assert len(sent)==1 and repo.get_target(t['id'])['round_trips']==0
    assert store.row('m1')['status']=='uncertain'


@pytest.mark.parametrize('stop_on_wait', [1, 2])
def test_stop_during_read_or_typing_wait(tmp_path, stop_on_wait):
    _, store, service, _, monitor, _ = ready(tmp_path)
    waits, reads, sends = [], [], []

    def sleep(seconds):
        waits.append(seconds)
        if len(waits) == stop_on_wait:
            monitor.stop()

    monitor.sleeper = sleep
    service.api.mark_as_read = lambda *args: reads.append(args)
    service.api.send_text = lambda *args: sends.append(args)
    assert store.ingest(incoming('100'))
    assert not monitor.run_cycle()
    assert reads == ([('u1', '100')] if stop_on_wait == 2 else [])
    assert not sends
    assert store.row('100')['status'] == 'archived'


def test_background_read_continues_while_another_chat_waits_for_ai(tmp_path, monkeypatch):
    from sweety_app import monitor as monitor_module

    repo, store, service, _, monitor, _ = ready(tmp_path)
    monitor.stop()
    second = store.add('u2', assignment())
    repo.update_target(second['id'], {'reply_enabled': True})
    monkeypatch.setattr(monitor_module.random, 'uniform', lambda *_: 0)
    ai_started, release_ai, second_read = Event(), Event(), Event()

    def generate_reply(**kwargs):
        ai_started.set()
        release_ai.wait(timeout=6)
        return ReplyDecision(incoming_summary='incoming', msg_reply='reply')

    def mark_as_read(mid, message_id):
        if (mid, message_id) == ('u2', '101'):
            second_read.set()

    monitor.ai.generate_reply = generate_reply
    service.api.mark_as_read = mark_as_read
    assert monitor.start()
    try:
        assert service.ingest(incoming('100'))
        assert ai_started.wait(timeout=2)
        assert service.ingest(incoming('101', **{'from': 'u2'}))
        assert second_read.wait(timeout=2)
    finally:
        release_ai.set()
        monitor.stop()


def test_renaming_contact_preserves_binding_and_assignments(tmp_path):
    repo,store,service=setup(tmp_path);t=store.add('u1',assignment())
    store.refresh_contacts([{'id':'u1','name':'新名字','blocked':False}])
    assert repo.get_target(t['id'])['name']=='新名字'
    assert repo.get_target(t['id'])['weapon_id']=='one-step-at-a-time'


def test_unaddressed_group_messages_are_context_only_and_retain_sender(tmp_path):
    repo,store,service=setup(tmp_path)
    store.refresh_contacts([{'id':'c1','name':'測試群組','kind':'group','blocked':False}])
    target=store.add('c1',assignment());repo.update_target(target['id'],{'reply_enabled':True})
    from sweety_app.monitor import MonitorController
    calls=[]
    monitor=MonitorController(repo,service,SimpleNamespace(generate_reply=lambda **kw:calls.append(kw)),sleeper=lambda _:None)
    service.start_receiving=lambda:None
    assert monitor.start(background=False)
    store.ingest({'id':'group-m1','from':'u-member','to':'c1','toType':2,'text':'群組內容','contentType':0,'createdTime':int(time.time()*1000)+10})
    monitor.run_cycle()
    assert calls==[]
    assert store.row('group-m1')['raw']=='{}'
    assert service.api.history[0]['text']=='群組內容'
    assert repo.get_target(target['id'])['round_trips']==0


@pytest.mark.parametrize('mid,kind,to_type', [('u1','person',0),('c1','group',2)])
def test_disabled_or_ended_targets_do_not_collect_messages(tmp_path,mid,kind,to_type):
    repo,store,service=setup(tmp_path)
    store.refresh_contacts([{'id':mid,'name':'Target','kind':kind,'blocked':False}])
    t=store.add(mid,assignment())
    message={'id':'off','from':'u-member' if kind=='group' else mid,'to':mid if kind=='group' else 'self',
             'toType':to_type,'text':'must not collect','createdTime':int(time.time()*1000)+100}
    assert not store.ingest(message)
    repo.update_target(t['id'],{'reply_enabled':True})
    repo.end_target(t['id'])
    assert not store.ingest({**message,'id':'ended'})
    assert store.rows()==[]


@pytest.mark.parametrize('provider,key_field',[('sweety','agnes_api_key'),('openai','openai_api_key')])
def test_start_requires_selected_provider_key_even_if_other_key_exists(tmp_path,provider,key_field):
    from sweety_app.monitor import MonitorController
    repo,store,service=setup(tmp_path)
    target=store.add('u1',assignment())
    repo.update_target(target['id'],{'reply_enabled':True})
    repo.update_settings({'ai_provider':provider,'agnes_api_key':'other-key' if provider=='openai' else '  ', 'openai_api_key':'other-key' if provider=='sweety' else '  '})
    receiver=[]
    service.start_receiving=lambda:receiver.append(True)
    monitor=MonitorController(repo,service,SimpleNamespace())
    assert not monitor.start(background=False)
    assert monitor.snapshot()['status']=='api_key_required'
    assert not monitor.snapshot()['enabled'] and receiver==[]
    repo.update_settings({key_field:'user-key'})
    assert monitor.start(background=False)
    monitor.stop()

@pytest.mark.parametrize('limit',[4,6,30])
def test_worker_respects_history_setting(tmp_path,limit):
    repo,store,service,target,monitor,calls=ready(tmp_path)
    repo.update_settings({'history_limit':limit})
    service.api.history=[incoming(f'past-{i}',f'past-{i}',createdTime=int(time.time()*1000)-10000+i) for i in range(40)]
    store.ingest(incoming('new-message'))
    assert monitor.run_cycle()
    assert len(calls[0]['history'])==limit
    assert all(m['content'].startswith('past-') for m in calls[0]['history'])


def test_login_failure_keeps_message_cause_and_traceback(tmp_path):
    _,store,service=setup(tmp_path)
    class LineAuthError(Exception): pass
    def fail_login(**kwargs):
        try:
            raise OSError('TLS handshake failed on Windows')
        except OSError as cause:
            error=LineAuthError('QR session rejected: code=401')
            error.reason='Device certificate rejected'
            error.status=401
            error.path='/api/auth/qr'
            raise error from cause
    service.factory=lambda:SimpleNamespace(qr_login=fail_login,close=lambda:None)
    service.state={'status':'connecting','expiresAt':time.time()+180}
    service._login(service.generation)
    error=service.snapshot()['error']
    assert 'QR session rejected: code=401' in error
    assert 'TLS handshake failed on Windows' in error
    assert 'Device certificate rejected' in error
    assert '/api/auth/qr' in error
    assert 'status=401' in error
    assert 'Traceback' in error
    assert 'fail_login' in error
    assert service.snapshot()['qr']=='' and service.snapshot()['pin']==''
