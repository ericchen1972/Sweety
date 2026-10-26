"""ChatGPT-authenticated Codex inference over the official local App Server protocol."""
from collections import deque
from contextlib import contextmanager
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from urllib.parse import urlparse


class CodexError(RuntimeError):
    """Only stable error codes leave this boundary; server bodies may contain private data."""


def discover_codex(*, candidates=None, which=shutil.which):
    if candidates is None:
        roots = [Path('/Applications'), Path.home() / 'Applications']
        candidates = [root / relative for root in roots for relative in (
            'ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex',
            'Codex.app/Contents/Resources/codex',
        )] + [Path.home() / '.local/bin/codex']
        if os.name == 'nt':
            candidates += [Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs/Codex/resources/codex.exe']
    for path in candidates:
        if Path(path).is_file() and os.access(path, os.X_OK):
            return str(path)
    return which('codex')


def strict_schema(value):
    if isinstance(value, list):
        return [strict_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {k: strict_schema(v) for k, v in value.items() if k != 'default'}
    if result.get('type') == 'object':
        result.update(required=list(result.get('properties', {})), additionalProperties=False)
    return result


def error_code(error):
    message = json.dumps(error, ensure_ascii=False).lower()
    if any(s in message for s in ('usage_limit', 'rate_limit', 'quota_exceeded')):
        return 'codex_rate_limited'
    if any(s in message for s in ('unauthorized', 'authentication', 'token_expired')):
        return 'codex_login_required'
    if any(s in message for s in ('model_not_found', 'unsupported_model', 'model_not_available')):
        return 'codex_model_unavailable'
    return 'codex_request_failed'


class _Rpc:
    def __init__(self, process, timeout):
        self.process = process
        self.deadline = time.monotonic() + timeout
        self.sequence = 0
        self.events = queue.Queue()
        self.pending = deque()
        self.closed = threading.Event()
        self.close_lock = threading.Lock()

        def read():
            try:
                for line in process.stdout:
                    self.events.put(json.loads(line))
                    if self.closed.is_set():
                        break
            except (ValueError, OSError):
                pass
            finally:
                self.events.put(None)
        threading.Thread(target=read, daemon=True, name='SweetyCodexRpc').start()

    def send(self, value):
        if self.closed.is_set():
            raise CodexError('codex_cancelled')
        try:
            self.process.stdin.write(json.dumps(value, ensure_ascii=False) + '\n')
            self.process.stdin.flush()
        except (OSError, ValueError) as exc:
            raise CodexError('codex_cancelled' if self.closed.is_set() else 'codex_disconnected') from exc

    def receive(self):
        while time.monotonic() < self.deadline:
            if self.closed.is_set():
                raise CodexError('codex_cancelled')
            try:
                event = self.events.get(timeout=min(.2, max(.001, self.deadline - time.monotonic())))
            except queue.Empty:
                continue
            if self.closed.is_set():
                raise CodexError('codex_cancelled')
            if event is None:
                raise CodexError('codex_disconnected')
            if 'method' in event and 'id' in event:
                self.send({'id': event['id'], 'error': {'code': -32601, 'message': 'No interactive tools in Sweety inference'}})
                raise CodexError('codex_unexpected_tool')
            return event
        raise CodexError('codex_timeout')

    def next(self):
        if self.closed.is_set():
            raise CodexError('codex_cancelled')
        return self.pending.popleft() if self.pending else self.receive()

    def request(self, method, params):
        self.sequence += 1
        sequence = self.sequence
        self.send({'id': sequence, 'method': method, 'params': params})
        while True:
            event = self.receive()
            if event.get('id') != sequence:
                if 'method' in event:
                    self.pending.append(event)
                continue
            if 'error' in event:
                raise CodexError(error_code(event['error']))
            return event.get('result', {})

    def close(self):
        with self.close_lock:
            if self.closed.is_set():
                return
            self.closed.set()
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                self.process.kill()
                self.process.wait(timeout=3)


class CodexService:
    def __init__(self, *, executable=discover_codex, process_factory=subprocess.Popen,
                 work_root=None, timeout=90):
        self.executable = executable
        self.process_factory = process_factory
        self.work_root = Path(work_root or Path.home() / 'Documents/Codex-Temp/sweety-codex')
        self.timeout = timeout
        self.lock = threading.RLock()
        self.sessions = set()
        self.login_rpc = None
        self.login_error = None
        self.cached_status = None
        self.cached_at = 0

    @contextmanager
    def session(self, *, timeout=None, authenticated=True):
        executable = self.executable()
        if not executable:
            raise CodexError('codex_not_installed')
        command = [executable, 'app-server', '--stdio', '-c', 'model_provider="openai"']
        for feature in ('shell_tool', 'multi_agent', 'apps', 'plugins', 'computer_use',
                        'browser_use', 'browser_use_external', 'hooks', 'memories',
                        'image_generation', 'view_image', 'workspace_dependencies'):
            command += ['--disable', feature]
        self.work_root.mkdir(parents=True, exist_ok=True)
        try:
            process = self.process_factory(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, bufsize=1, cwd=str(self.work_root))
        except OSError as exc:
            raise CodexError('codex_unavailable') from exc
        rpc = _Rpc(process, self.timeout if timeout is None else timeout)
        with self.lock:
            self.sessions.add(rpc)
        try:
            rpc.request('initialize', {'clientInfo': {'name': 'Sweety', 'version': '2.0.2'}})
            rpc.send({'method': 'initialized', 'params': {}})
            if authenticated:
                account = rpc.request('account/read', {'refreshToken': False}).get('account') or {}
                if account.get('type') not in ('chatgpt', 'chatgptAuthTokens'):
                    raise CodexError('codex_login_required')
                rpc.account = account
            yield rpc
        finally:
            rpc.close()
            with self.lock:
                self.sessions.discard(rpc)

    def status(self, refresh=False):
        available = bool(self.executable())
        if not available:
            return {'available': False, 'ready': False, 'status': 'codex_not_installed'}
        with self.lock:
            if not refresh and self.cached_status and time.monotonic() - self.cached_at < 5:
                return dict(self.cached_status, loginPending=self.login_rpc is not None, loginError=self.login_error)
        try:
            with self.session(timeout=15) as rpc:
                result = {'available': True, 'ready': True, 'status': 'codex_ready',
                          'planType': rpc.account.get('planType')}
        except CodexError as exc:
            result = {'available': True, 'ready': False, 'status': str(exc)}
        with self.lock:
            self.cached_status, self.cached_at = result, time.monotonic()
            return dict(result, loginPending=self.login_rpc is not None, loginError=self.login_error)

    def login(self):
        # The process must remain alive while its browser OAuth callback is pending.
        with self.lock:
            if self.login_rpc is not None:
                raise CodexError('codex_login_pending')
            self.login_rpc = True
            self.login_error = None
        context = self.session(timeout=300, authenticated=False)
        try:
            rpc = context.__enter__()
            result = rpc.request('account/login/start', {'type': 'chatgpt'})
            url = result.get('authUrl', '')
            parsed = urlparse(url)
            if parsed.scheme != 'https' or parsed.hostname not in ('auth.openai.com', 'chatgpt.com', 'auth0.openai.com'):
                raise CodexError('codex_login_failed')
        except Exception:
            context.__exit__(None, None, None)
            with self.lock:
                self.login_rpc = None
            raise
        with self.lock:
            self.login_rpc = rpc

        def wait_for_login():
            try:
                while True:
                    event = rpc.next()
                    if event.get('method') == 'account/login/completed':
                        if not event.get('params', {}).get('success'):
                            raise CodexError('codex_login_failed')
                        break
            except CodexError as exc:
                with self.lock:
                    self.login_error = str(exc)
            finally:
                context.__exit__(None, None, None)
                with self.lock:
                    self.login_rpc = None
                    self.cached_status = None
        threading.Thread(target=wait_for_login, daemon=True, name='SweetyCodexLogin').start()
        return {'authUrl': url}

    def cancel(self):
        with self.lock:
            sessions = list(self.sessions)
        for rpc in sessions:
            rpc.close()

    def decide(self, *, messages, schema):
        with self.session() as rpc:
            models, cursor, seen = [], None, set()
            while True:
                page = rpc.request('model/list', {'limit': 100, 'includeHidden': False, **({'cursor': cursor} if cursor else {})})
                models += [m for m in page.get('data', []) if not m.get('hidden')]
                cursor = page.get('nextCursor')
                if not cursor:
                    break
                if cursor in seen:
                    raise CodexError('codex_model_unavailable')
                seen.add(cursor)
            images = [part['image_url']['url'] for m in messages if isinstance(m['content'], list)
                      for part in m['content'] if part.get('type') == 'image_url']
            eligible = [m for m in models if not images or 'image' in (m.get('inputModalities') or [])]
            model = next((m for m in eligible if m.get('isDefault')), next(iter(eligible), None))
            if not model:
                raise CodexError('codex_model_unavailable')
            config = rpc.request('config/read', {'includeLayers': True})
            overrides = {'web_search': 'disabled'}
            for layer in [config.get('config', {})] + [l.get('config', {}) for l in config.get('layers') or []]:
                for name in layer.get('mcp_servers', {}):
                    overrides[f'mcp_servers.{name}.enabled'] = False
            instructions = '\n\n'.join(m['content'] for m in messages if m['role'] == 'system')
            # Keep role boundaries in explicit data; images are attached in the same order.
            transcript = []
            for message in messages:
                if message['role'] == 'system':
                    continue
                content = message['content']
                if isinstance(content, list):
                    content = [p if p.get('type') == 'text' else {'type': 'attached_image'} for p in content]
                transcript.append({'role': message['role'], 'content': content})
            with tempfile.TemporaryDirectory(prefix='inference-', dir=self.work_root) as cwd:
                thread = rpc.request('thread/start', {'cwd': cwd, 'ephemeral': True,
                    'approvalPolicy': 'never', 'sandbox': 'read-only', 'config': overrides,
                    'developerInstructions': instructions + '\n只分析提供的對話資料並輸出指定 JSON。不可使用工具、操作 App 或建立檔案。'})['thread']['id']
                inputs = [{'type': 'text', 'text': json.dumps({'conversation': transcript}, ensure_ascii=False)}]
                inputs += [{'type': 'image', 'url': url} for url in images]
                turn = rpc.request('turn/start', {'threadId': thread, 'model': model['model'],
                    'input': inputs, 'outputSchema': strict_schema(schema)})['turn']['id']
                output = None
                while True:
                    event = rpc.next()
                    params = event.get('params', {})
                    if params.get('threadId') != thread:
                        continue
                    if event.get('method') in ('item/started', 'item/completed'):
                        item = params.get('item', {})
                        if item.get('type') in ('commandExecution', 'fileChange', 'mcpToolCall', 'dynamicToolCall', 'webSearch', 'imageGeneration'):
                            raise CodexError('codex_unexpected_tool')
                        if event['method'] == 'item/completed' and params.get('turnId') == turn and item.get('type') == 'agentMessage' and item.get('phase') in (None, 'final_answer'):
                            output = item.get('text')
                    if event.get('method') == 'turn/completed' and params.get('turn', {}).get('id') == turn:
                        if params['turn'].get('status') != 'completed':
                            raise CodexError(error_code(params['turn'].get('error', {})))
                        try:
                            value = json.loads(output or '')
                        except ValueError as exc:
                            raise CodexError('codex_invalid_result') from exc
                        if not isinstance(value, dict):
                            raise CodexError('codex_invalid_result')
                        return value

    def test(self):
        result = self.decide(messages=[{'role': 'system', 'content': 'Return {"ok":true}.'},
            {'role': 'user', 'content': 'Connection test only.'}],
            schema={'type': 'object', 'properties': {'ok': {'type': 'boolean'}}, 'required': ['ok'], 'additionalProperties': False})
        if result.get('ok') is not True:
            raise CodexError('codex_invalid_result')
        return {'ready': True, 'status': 'codex_verified'}
