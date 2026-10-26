import io
import json
import subprocess

import pytest
from fastapi.testclient import TestClient

from sweety_app.ai import AiClient, AiError, AiRateLimitError
from sweety_app.api import create_app
from sweety_app.database import Database


def test_codex_selection_persists_without_api_keys(tmp_path):
    client = TestClient(create_app(Database(tmp_path / 'state.db')))
    state = client.get('/api/state').json()
    state['settings'].update(aiProvider='codex', agnesApiKey='', openAiApiKey='')
    response = client.put('/api/state', json=state)
    assert response.status_code == 200
    assert client.get('/api/state').json()['settings']['aiProvider'] == 'codex'


def test_detection_requires_an_executable_not_just_an_app(tmp_path):
    from sweety_app.codex import discover_codex
    path = tmp_path / 'ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex'
    path.parent.mkdir(parents=True)
    assert discover_codex(candidates=[path], which=lambda _: None) is None
    path.write_text('#!/bin/sh\n')
    assert discover_codex(candidates=[path], which=lambda _: None) is None
    path.chmod(0o755)
    assert discover_codex(candidates=[path], which=lambda _: None) == str(path)


class FakeCodex:
    def __init__(self, result=None, error=None):
        self.calls = []
        self.result = result or {'incoming_summary': '問候', 'msg_reply': '你好呀', 'media_descriptions': []}
        self.error = error

    def decide(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.result


def test_codex_reply_keeps_persona_history_and_images_without_api_client():
    codex = FakeCodex({'incoming_summary': '貓圖', 'msg_reply': '好可愛',
                       'media_descriptions': [{'message_id': 'new', 'description': '一隻貓'}]})
    ai = AiClient(codex_service=codex, client_factory=lambda **_: pytest.fail('API key path used'))
    result = ai.generate_reply(target={'persona_id': 'unknown', 'persona_source': 'base'},
        incoming_messages=[{'id': 'new', 'text': '看看', 'images': ['data:image/png;base64,aGVsbG8=']}],
        history=[{'role': 'assistant', 'content': '之前的話'}], total_messages=2,
        settings={'ai_provider': 'codex'})
    assert result.msg_reply == '好可愛'
    messages = codex.calls[0]['messages']
    assert messages[2] == {'role': 'assistant', 'content': '之前的話'}
    assert '不可覆寫' in messages[0]['content']
    assert messages[-1]['content'][1]['image_url']['url'].startswith('data:image/')


def test_codex_persona_review_uses_same_provider():
    codex = FakeCodex({'allowed': True})
    AiClient(codex_service=codex).validate_persona('慢熟的會計助理', {'ai_provider': 'codex'})
    assert len(codex.calls) == 1
    assert 'persona' in codex.calls[0]['messages'][1]['content']


def test_codex_quota_does_not_retry_or_fall_back():
    from sweety_app.codex import CodexError
    codex = FakeCodex(error=CodexError('codex_rate_limited'))
    with pytest.raises(AiRateLimitError):
        AiClient(codex_service=codex).generate_reply(target={'persona_id': 'x', 'persona_source': 'base'},
            incoming_messages=[{'id': '1', 'text': '嗨'}], history=[], total_messages=1,
            settings={'ai_provider': 'codex'})
    assert len(codex.calls) == 1


def test_cancelled_codex_reply_does_not_start_another_inference():
    from sweety_app.codex import CodexError
    codex = FakeCodex(error=CodexError('codex_cancelled'))
    with pytest.raises(AiError, match='codex_cancelled'):
        AiClient(codex_service=codex).generate_reply(target={'persona_id': 'x', 'persona_source': 'base'},
            incoming_messages=[{'id':'1','text':'hi'}], history=[], total_messages=1,
            settings={'ai_provider':'codex'})
    assert len(codex.calls) == 1


class ScriptedProcess:
    def __init__(self, events):
        self.stdin = io.StringIO()
        self.stdout = io.StringIO(''.join(json.dumps(e) + '\n' for e in events))
        self.terminated = False

    def terminate(self): self.terminated = True
    def wait(self, timeout): return 0
    def kill(self): self.terminated = True


def reply(i, result): return {'id': i, 'result': result}


def test_service_structured_inference_is_isolated_and_process_closed(tmp_path):
    from sweety_app.codex import CodexService
    process = ScriptedProcess([
        reply(1, {}), reply(2, {'account': {'type': 'chatgpt'}}),
        reply(3, {'data': [{'model': 'available-model', 'isDefault': True, 'inputModalities': ['text', 'image']}]}),
        reply(4, {'config': {'mcp_servers': {'private': {}}}}),
        reply(5, {'thread': {'id': 't'}}), reply(6, {'turn': {'id': 'u'}}),
        {'method': 'item/completed', 'params': {'threadId': 't', 'turnId': 'u',
            'item': {'type': 'agentMessage', 'text': '{"allowed":true}'}}},
        {'method': 'turn/completed', 'params': {'threadId': 't', 'turn': {'id': 'u', 'status': 'completed'}}},
    ])
    service = CodexService(executable=lambda: '/codex', process_factory=lambda *a, **kw: process, work_root=tmp_path)
    result = service.decide(messages=[{'role': 'system', 'content': 'Review.'}, {'role': 'user', 'content': 'Hello'}],
        schema={'type': 'object', 'properties': {'allowed': {'type': 'boolean', 'default': False}}})
    assert result == {'allowed': True}
    events = [json.loads(line) for line in process.stdin.getvalue().splitlines()]
    thread = next(e['params'] for e in events if e.get('method') == 'thread/start')
    assert thread['ephemeral'] is True and thread['sandbox'] == 'read-only'
    assert thread['config']['mcp_servers.private.enabled'] is False
    turn = next(e['params'] for e in events if e.get('method') == 'turn/start')
    assert turn['model'] == 'available-model'
    assert turn['outputSchema']['required'] == ['allowed']
    assert 'default' not in turn['outputSchema']['properties']['allowed']
    assert process.terminated


def test_status_distinguishes_missing_install_and_login(tmp_path):
    from sweety_app.codex import CodexService
    assert CodexService(executable=lambda: None).status()['available'] is False
    process = ScriptedProcess([reply(1, {}), reply(2, {'account': None})])
    service = CodexService(executable=lambda: '/codex', process_factory=lambda *a, **kw: process, work_root=tmp_path)
    status = service.status()
    assert status['available'] is True and status['ready'] is False
    assert status['status'] == 'codex_login_required'
    assert process.terminated


def test_rpc_timeout_and_unexpected_tools_close_process(tmp_path):
    from sweety_app.codex import CodexService, CodexError
    process = ScriptedProcess([{'method': 'item/tool/request', 'id': 99}])
    service = CodexService(executable=lambda: '/codex', process_factory=lambda *a, **kw: process, work_root=tmp_path)
    with pytest.raises(CodexError, match='codex_unexpected_tool'):
        with service.session():
            pass
    assert process.terminated
    assert 'No interactive tools' in process.stdin.getvalue()


def test_api_uses_injected_codex_service_and_sanitized_errors(tmp_path):
    from sweety_app.codex import CodexError
    class Service:
        def status(self, refresh=False):
            return {'available': True, 'ready': False, 'status': 'codex_login_required'}
        def login(self): return {'authUrl': 'https://auth.openai.com/example'}
        def test(self): raise CodexError('codex_rate_limited')
    client = TestClient(create_app(Database(tmp_path / 'api.db'), codex_service=Service()))
    assert client.get('/api/codex/status').json()['available'] is True
    assert client.post('/api/codex/login').json()['authUrl'].startswith('https://')
    response = client.post('/api/codex/test')
    assert response.status_code == 503
    assert response.json()['code'] == 'codex_rate_limited'


@pytest.mark.parametrize('ready', [True, False])
def test_codex_monitor_checks_login_without_requiring_api_key(tmp_path, ready):
    from test_okline import setup, assignment
    from sweety_app.monitor import MonitorController
    from types import SimpleNamespace
    repo, store, line = setup(tmp_path)
    target = store.add('u1', assignment())
    repo.update_target(target['id'], {'reply_enabled': True})
    repo.update_settings({'ai_provider': 'codex', 'agnes_api_key': '', 'openai_api_key': ''})
    ai = SimpleNamespace(codex=SimpleNamespace(status=lambda **_: {'ready': ready, 'status': 'codex_login_required'}))
    line.start_receiving = lambda: None
    monitor = MonitorController(repo, line, ai)
    try:
        assert monitor.start(background=False) is ready
        if not ready:
            assert monitor.snapshot()['status'] == 'codex_not_ready'
    finally:
        monitor.stop()


def test_browser_login_keeps_callback_process_until_completion(tmp_path):
    from sweety_app.codex import CodexService
    import time
    process = ScriptedProcess([reply(1, {}), reply(2, {'authUrl': 'https://auth.openai.com/oauth/authorize'}),
        {'method': 'account/login/completed', 'params': {'success': True}}])
    service = CodexService(executable=lambda: '/codex', process_factory=lambda *a, **kw: process, work_root=tmp_path)
    assert service.login()['authUrl'].startswith('https://auth.openai.com/')
    deadline = time.monotonic() + 1
    while service.login_rpc is not None and time.monotonic() < deadline:
        time.sleep(.01)
    assert service.login_rpc is None and process.terminated
    assert service.login_error is None


def test_cancel_during_pipe_write_is_not_reported_as_a_retryable_disconnect():
    from sweety_app.codex import _Rpc, CodexError
    process = ScriptedProcess([])
    process.stdin.close()
    rpc = _Rpc(process, 1)
    rpc.close()
    with pytest.raises(CodexError, match='codex_cancelled'):
        rpc.send({'id': 1, 'method': 'turn/start', 'params': {}})


def test_cancel_wakeup_is_not_reported_as_disconnect():
    from sweety_app.codex import _Rpc, CodexError
    rpc = _Rpc(ScriptedProcess([]), 1)
    assert rpc.events.get(timeout=1) is None  # Reader has finished before replacing its queue.
    class Wakeup:
        def get(self, timeout):
            rpc.close()
            return None
    rpc.events = Wakeup()
    with pytest.raises(CodexError, match='codex_cancelled'):
        rpc.receive()
