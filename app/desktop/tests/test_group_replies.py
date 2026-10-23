import json,time
import pytest
from test_okline import setup, assignment
from sweety_app.ai import ReplyDecision
from sweety_app.monitor import MonitorController


def group_ready(tmp_path,names='小美,美姐'):
    repo,store,service=setup(tmp_path)
    repo.update_settings({'user_names':names})
    store.refresh_contacts([{'id':'c1','name':'群組','kind':'group','blocked':False}])
    target=store.add('c1',assignment());repo.update_target(target['id'],{'reply_enabled':True})
    calls=[];sent=[]
    class AI:
        def generate_reply(self,**kw):
            calls.append(kw);return ReplyDecision(incoming_summary='incoming',msg_reply='群組回覆')
    service.api.send_text=lambda mid,text:(sent.append((mid,text)) or {'id':'group-receipt'})
    service.start_receiving=lambda:None
    monitor=MonitorController(repo,service,AI(),sleeper=lambda _:None)
    assert monitor.start(background=False)
    return repo,store,service,target,monitor,calls,sent


def group_message(text,mention=None,sender='member',mid='g1'):
    return {'id':mid,'from':sender,'to':'c1','toType':2,'contentType':0,'text':text,
            'createdTime':int(time.time()*1000)+50,
            'contentMetadata':{'MENTION':mention} if mention is not None else {}}


@pytest.mark.parametrize('text,mention,names',[
    ('小美你好',None,'小美,美姐'),('美姐在嗎',None,'小美， 美姐'),
    ('ALICE hello',None,'Alice'),('你好',json.dumps({'MENTIONEES':[{'M':'self'}]}),''),
    ('你好',{'MENTIONEES':[{'M':'self'}]},''),
])
def test_name_or_real_self_mention_triggers_group_reply(tmp_path,text,mention,names):
    repo,store,service,t,monitor,calls,sent=group_ready(tmp_path,names)
    assert store.ingest(group_message(text,mention))
    assert monitor.run_cycle()
    assert sent==[('c1','群組回覆')] and len(calls)==1
    assert calls[0]['incoming_messages'][0]['senderId']=='member'
    assert calls[0]['incoming_messages'][0]['chatId']=='c1'
    assert repo.get_target(t['id'])['round_trips']==1
    assert not store.ingest(group_message(text,mention))
    assert not monitor.run_cycle() and len(sent)==1


@pytest.mark.parametrize('text,mention,sender,names',[
    ('大家好',None,'member','小美'),('你好',{'MENTIONEES':[{'M':'someone-else'}]},'member',''),
    ('你好','invalid json','member',''),('你好',{'MENTIONEES':'invalid'},'member',''),
    ('小美你好',None,'self','小美'),('大家好',None,'member',' ,， '),
])
def test_unrelated_and_self_group_messages_never_reply(tmp_path,text,mention,sender,names):
    repo,store,service,t,monitor,calls,sent=group_ready(tmp_path,names)
    store.ingest(group_message(text,mention,sender));monitor.run_cycle()
    assert calls==[] and sent==[] and repo.get_target(t['id'])['round_trips']==0


def test_group_stop_during_ai_and_history_never_send(tmp_path):
    repo,store,service,t,monitor,calls,sent=group_ready(tmp_path)
    store.ingest(group_message('小美 old',mid='history'),context_only=True)
    monitor.run_cycle();assert sent==[]
    def ai(**kw):
        monitor.stop();return ReplyDecision(incoming_summary='小美',msg_reply='late')
    monitor.ai.generate_reply=ai
    store.ingest(group_message('小美 now'));monitor.run_cycle()
    assert sent==[]


def test_user_names_survive_old_client_settings_update(tmp_path):
    repo,store,service=setup(tmp_path)
    assert repo.get_settings()['user_names']==''
    repo.update_settings({'user_names':'小美,美姐'})
    repo.update_settings({'reply_delay_min_seconds':0})
    assert repo.get_settings()['user_names']=='小美,美姐'


def test_user_names_api_round_trip_and_legacy_payload(tmp_path):
    from fastapi.testclient import TestClient
    from sweety_app.api import create_app
    repo,store,service=setup(tmp_path)
    client=TestClient(create_app(repo.database,line_service=service))
    state=client.get('/api/state').json()
    state['settings']['userNames']='小美,美姐'
    assert client.put('/api/state',json=state).json()['settings']['userNames']=='小美,美姐'
    del state['settings']['userNames']
    assert client.put('/api/state',json=state).json()['settings']['userNames']=='小美,美姐'
    assert client.put('/api/settings',json={**state['settings'],'userNames':'x'*501}).status_code==422
    assert client.put('/api/settings',json={**state['settings'],'userNames':''}).json()['userNames']==''
