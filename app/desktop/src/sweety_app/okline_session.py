"""Encrypted local session; encryption key stays in the user's Keychain."""
import hashlib
import json
import os
from pathlib import Path
import tempfile


class SessionVault:
    def __init__(self, directory, owner):
        self.directory=Path(directory)
        self.owner=hashlib.sha256(owner.encode()).hexdigest()
        self.path=self.directory/(self.owner+'.session')

    def cipher(self):
        import keyring
        from cryptography.fernet import Fernet
        key=keyring.get_password('Sweety.OkLine',self.owner)
        if not key:
            key=Fernet.generate_key().decode()
            keyring.set_password('Sweety.OkLine',self.owner,key)
        return Fernet(key.encode())

    def load(self):
        if not self.path.exists(): return None
        return json.loads(self.cipher().decrypt(self.path.read_bytes()))

    def save(self, value):
        encrypted=self.cipher().encrypt(json.dumps(value).encode())
        self.directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        fd,name=tempfile.mkstemp(dir=self.directory,prefix='.session-')
        try:
            with os.fdopen(fd,'wb') as f:
                f.write(encrypted);f.flush();os.fsync(f.fileno())
            os.replace(name,self.path)
        finally:
            if os.path.exists(name): os.unlink(name)

    def clear(self):
        self.path.unlink(missing_ok=True)


def node_path():
    import sys, shutil
    bundled=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/('runtime/node.exe' if sys.platform == 'win32' else 'runtime/node')
    if bundled.is_file(): return str(bundled)
    node=shutil.which('node')
    if node: return node
    # Native app development launched from Finder does not inherit shell PATH.
    candidates=sorted((Path.home()/'.nvm/versions/node').glob('*/bin/node'),reverse=True)
    if candidates: return str(candidates[0])
    raise ValueError('line_node_missing')


def enforce_sse_utf8(transport):
    """SSE is UTF-8, even when requests defaults text/* to ISO-8859-1.

    Set the response encoding before OkLine calls iter_lines(decode_unicode=True).
    Do not guess or rewrite already-decoded user text or ordinary JSON responses.
    """
    if getattr(transport,'_sweety_sse_utf8',False):return
    send=transport._send
    def utf8_send(*args,**kwargs):
        response=send(*args,**kwargs)
        if response.headers.get('Content-Type','').split(';',1)[0].strip().lower()=='text/event-stream':
            response.encoding='utf-8'
        return response
    transport._send=utf8_send
    transport._sweety_sse_utf8=True


def sdk_factory(vault=None, saved=None):
    from .background_processes import configure_line_background_processes
    configure_line_background_processes()
    from okline import OkLine
    from okline.transport import LineConfig
    from okline.session import Session
    class PrivateClient(OkLine):
        def next_req_seq(self):
            from .line_request_sequence import next_sequence
            from .config import DATABASE_PATH
            directory=vault.directory if vault is not None else DATABASE_PATH.parent/'line-sessions'
            return next_sequence(directory,self.tokens.mid)

        def save_tokens(self, path=None):
            if vault is not None:
                session=Session.from_tokens(self.tokens)
                if self.e2ee.is_ready(): session.e2ee=self.e2ee.export_keys()
                vault.save(session.to_dict())
    session=Session.from_dict(saved or {})
    api=PrivateClient(access_token=session.access_token,refresh_token=session.refresh_token,
                      certificate=session.certificate,mid=session.mid,record=False,
                      config=LineConfig(node_path=node_path(),max_retries=0),auto_refresh_schedule=False)
    enforce_sse_utf8(api.transport)
    if session.e2ee: api.e2ee.load_from_export(session.e2ee)
    api._session_path='encrypted-vault' if vault else None
    return api
