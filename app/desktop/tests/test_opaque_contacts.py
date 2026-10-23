import time
from test_okline import setup,assignment
from sweety_app.api import create_app
from fastapi.testclient import TestClient


def test_real_directory_ids_are_opaque_not_u_c_prefixed(tmp_path):
    repo,store,service=setup(tmp_path)
    store.refresh_contacts([{'id':'9f-person-opaque','name':'BoBo','kind':'person','blocked':False},
                            {'id':'8a-group-opaque','name':'測試群組','kind':'group','blocked':False}])
    rows=store.contacts()
    assert {"9f-person-opaque", "8a-group-opaque"} <= {r["id"] for r in rows}
    person=store.add('9f-person-opaque',assignment())
    group=store.add('8a-group-opaque',assignment())
    assert person['line_kind']=='person' and group['line_kind']=='group'
    client=TestClient(create_app(repo.database,line_service=service))
    targets=client.get('/api/state').json()['targets']
    assert {t['lineKind'] for t in targets}=={'person','group'}
    repo.update_target(person['id'],{'reply_enabled':True})
    assert store.ingest({'id':'m1','from':'9f-person-opaque','to':'self','contentType':0,'text':'hello','createdTime':int(time.time()*1000)+50})
