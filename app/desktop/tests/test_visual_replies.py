import base64,json,time
from io import BytesIO
from types import SimpleNamespace
import pytest
from PIL import Image
from test_okline import setup,assignment,incoming,ready
from test_group_replies import group_ready,group_message
from sweety_app.ai import ReplyDecision,build_messages


def png_bytes():
    out=BytesIO();Image.new('RGB',(120,80),'red').save(out,format='PNG');return out.getvalue()


@pytest.mark.parametrize('kind',[1,7])
def test_visual_input_triggers_reply_and_stores_description(tmp_path,kind):
    repo,store,service,t,monitor,calls=ready(tmp_path)
    service.image_inputs=lambda raw,**kw:['data:image/jpeg;base64,'+base64.b64encode(png_bytes()).decode()]
    def ai(**kw):
        calls.append(kw)
        return ReplyDecision(incoming_summary='紅色畫面',msg_reply='你傳了紅色的圖呀？',media_descriptions=[{'message_id':'visual','description':'紅色畫面'}])
    monitor.ai.generate_reply=ai
    store.ingest(incoming('visual','',contentType=kind,contentMetadata={'STKID':'52002734'}))
    assert monitor.run_cycle()
    assert len(calls)==1 and calls[0]['incoming_messages'][0]['images']
    assert any('紅色畫面' in m['content'] for m in repo.list_messages(t['id']))
    assert repo.get_target(t['id'])['round_trips']==1
    assert not store.ingest(incoming('visual','',contentType=kind))


def test_media_download_failure_never_generates_from_old_text(tmp_path):
    repo,store,service,t,monitor,calls=ready(tmp_path)
    def failed(*a,**kw):raise ValueError('unavailable')
    service.image_inputs=failed
    store.ingest(incoming('image','',contentType=1))
    assert not monitor.run_cycle() and calls==[]
    assert repo.get_target(t['id'])['round_trips']==0
    assert store.row('image')['status']=='failed'


def test_stop_during_download_never_calls_ai(tmp_path):
    repo,store,service,t,monitor,calls=ready(tmp_path)
    def download(*a,**kw):monitor.stop();return ['data:image/jpeg;base64,abc']
    service.image_inputs=download
    store.ingest(incoming('image','',contentType=1));monitor.run_cycle()
    assert calls==[] and repo.get_target(t['id'])['round_trips']==0


def test_group_image_requires_existing_mention_or_name_gate(tmp_path):
    repo,store,service,t,monitor,calls,sent=group_ready(tmp_path)
    service.image_inputs=lambda *a,**kw:['data:image/jpeg;base64,abc']
    for mid,meta,status in [('no',{},'context'),('yes',{'MENTION':json.dumps({'MENTIONEES':[{'M':'self'}]})},'pending')]:
        message={**group_message('',mid=mid),'contentType':1,'contentMetadata':meta}
        store.ingest(message);assert store.row(mid)['status']==status


def test_multimodal_prompt_associates_visuals_with_message_id():
    messages=build_messages(system_prompt_template='任務 {persona_text}',persona_text='自然',history=[],total_messages=0,
        incoming_messages=[{'id':'one','text':'看看這個','images':['data:image/jpeg;base64,abc']},{'id':'two','text':'下一句'}])
    content=messages[-1]['content']
    assert isinstance(content,list)
    assert any(p.get('image_url',{}).get('url')=='data:image/jpeg;base64,abc' for p in content)
    text=' '.join(p.get('text','') for p in content)
    assert 'one' in text and 'two' in text and '看看這個' in text
    assert 'base64,abc' not in text


def test_image_encoding_has_size_limits_and_no_ocr():
    from sweety_app.visual_media import encode_images,MediaError
    urls=encode_images(png_bytes())
    assert len(urls)==1 and urls[0].startswith('data:image/jpeg;base64,')
    with pytest.raises(MediaError):encode_images(b'not an image')
    with pytest.raises(MediaError):encode_images(b'a'*(12*1024*1024+1))


def test_sticker_download_uses_only_numeric_line_cdn_ids():
    from sweety_app.visual_media import sticker_urls,MediaError
    urls=sticker_urls({'contentMetadata':{'STKID':'52002734'}})
    assert urls[0]=='https://stickershop.line-scdn.net/stickershop/v1/sticker/52002734/android/sticker.png'
    with pytest.raises(MediaError):sticker_urls({'contentMetadata':{'STKID':'../../secret'}})


def test_decoded_sealed_image_download_uses_enc_km(tmp_path,monkeypatch):
    from sweety_app import visual_media
    repo,store,service=setup(tmp_path)
    encrypted=b'encrypted';key=b'k'*32
    service.api.obs=SimpleNamespace(download_object=lambda *a,**kw:encrypted)
    monkeypatch.setattr(visual_media,'download_obs_bytes',lambda *a:encrypted)
    monkeypatch.setattr(visual_media,'decrypt_image_blob',lambda k,b:png_bytes() if k==key and b==encrypted else b'bad')
    result=service.image_inputs({'id':'e2ee','contentType':1,'contentMetadata':{'ENC_KM':base64.b64encode(key).decode(),'OID':'opaque','SID':'em'}})
    assert result[0].startswith('data:image/jpeg;base64,')


def test_real_letter_sealing_blob_round_trip(tmp_path,monkeypatch):
    from sweety_app import visual_media
    from okline.e2ee_crypto import encrypt_blob
    repo,store,service=setup(tmp_path)
    key=b'x'*32;encrypted=encrypt_blob(key,png_bytes())
    monkeypatch.setattr(visual_media,'download_obs_bytes',lambda *a:encrypted)
    urls=service.image_inputs({'id':'sealed','contentType':1,'contentMetadata':{'ENC_KM':base64.b64encode(key).decode(),'OID':'opaque','SID':'em'}})
    assert urls[0].startswith('data:image/jpeg;base64,')


def test_media_descriptions_are_required_before_sending(tmp_path):
    repo,store,service,t,monitor,calls=ready(tmp_path)
    service.image_inputs=lambda *a,**kw:['data:image/jpeg;base64,abc']
    store.ingest(incoming('visual','',contentType=1))
    # Existing fake AI returns only a text decision, which cannot silently pass as vision.
    assert not monitor.run_cycle()
    assert repo.get_target(t['id'])['round_trips']==0


def test_visual_batches_remain_queued_instead_of_dropped(tmp_path):
    repo,store,service,t,monitor,calls=ready(tmp_path)
    sent=[];service.api.send_text=lambda *a:(sent.append(a) or {'id':str(len(sent))})
    service.image_inputs=lambda *a,**kw:['data:image/jpeg;base64,abc']
    def ai(**kw):
        calls.append(kw)
        return ReplyDecision(incoming_summary='圖',msg_reply='回覆',media_descriptions=[{'message_id':m['id'],'description':'紅色圖案'} for m in kw['incoming_messages']])
    monitor.ai.generate_reply=ai
    for i in range(10):store.ingest(incoming('visual-'+str(i),'',contentType=1))
    assert monitor.run_cycle() and len(calls[0]['incoming_messages'])==8
    assert monitor.run_cycle() and len(calls[1]['incoming_messages'])==2
    assert repo.get_target(t['id'])['round_trips']==2


def test_image_stream_aborts_at_limit_even_without_declared_size():
    from sweety_app.visual_media import download_obs_bytes,MediaError,MAX_MEDIA_BYTES
    consumed=[];closed=[];options=[]
    class Response:
        headers={}
        def __enter__(self):return self
        def __exit__(self,*a):closed.append(True)
        def raise_for_status(self):pass
        def iter_content(self,size):
            for i in range(30):
                consumed.append(i);yield b'x'*(1024*1024)
    transport=SimpleNamespace(base_headers=lambda **kw:{},_send=lambda *a,**kw:(options.append(kw) or Response()))
    obs=SimpleNamespace(_t=transport,_obs_base=lambda:'https://obs.line-apps.com',_obs_auth=lambda path:{},_talk_meta_header=lambda *a,**kw:{})
    with pytest.raises(MediaError):download_obs_bytes(SimpleNamespace(obs=obs),'m','opaque','id')
    assert len(consumed)==13 and closed==[True] and options[0]['stream'] is True
