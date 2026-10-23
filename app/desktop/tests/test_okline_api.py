from fastapi.testclient import TestClient
from test_okline import setup, assignment
from sweety_app.api import create_app


def test_directory_bind_and_bulk_state_cannot_overwrite_server_identity(tmp_path):
    repo,store,service=setup(tmp_path)
    old=repo.create_target(assignment());repo.record_exchange(old['id'],'old','reply')
    client=TestClient(create_app(repo.database,line_service=service))
    assert len(client.get('/api/line/contacts').json())==3
    state=client.get('/api/state').json()
    assert not state['targets'][0]['lineBound']
    assert client.post('/api/line/targets/bind',json={'targetId':old['id'],'contactId':'u1'}).status_code==200
    # A browser tab that was opened before binding must not revert the MID/name/metrics.
    assert client.put('/api/state',json=state).status_code==200
    t=client.get('/api/state').json()['targets'][0]
    assert t['lineBound'] and t['name']=='同名 😊' and t['roundTrips']==1
    assert client.post('/api/line/targets/bind',json={'targetId':old['id'],'contactId':'u2'}).status_code==400
    service.store.activate('other')
    assert not client.get('/api/state').json()['targets'][0]['lineAvailable']


def test_enroll_requires_real_contact_and_preserves_assignment(tmp_path):
    repo,store,service=setup(tmp_path)
    client=TestClient(create_app(repo.database,line_service=service))
    payload={'contactId':'u2','assignment':{'name':'ignored','ageGroup':'20-35','gender':'female','personaId':'cautious-accounting-assistant','personaSource':'base','weaponId':'one-step-at-a-time','weaponSource':'base','replyEnabled':True}}
    response=client.post('/api/line/contacts/add',json=payload)
    assert response.status_code==201
    t=response.json();assert t['name']=='同名 😊' and not t['replyEnabled']
    payload['contactId']='u3';assert client.post('/api/line/contacts/add',json=payload).status_code==400
