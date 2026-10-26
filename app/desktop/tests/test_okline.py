import time
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
    store.ingest(incoming('own',text='manual',**{'from':'self','to':'u1'}))
    monitor.run_cycle(); assert calls==[]
    assert repo.get_target(t['id'])['round_trips']==0
    store.ingest(incoming('text'))
    monitor.run_cycle(); assert len(calls)==1
    assert any(x['content']=='manual' and x['role']=='assistant' for x in calls[0]['history'])


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
    store.ingest(incoming('m1'));monitor.run_cycle();monitor.run_cycle()
    assert len(sent)==1 and repo.get_target(t['id'])['round_trips']==0
    assert store.row('m1')['status']=='uncertain'


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
