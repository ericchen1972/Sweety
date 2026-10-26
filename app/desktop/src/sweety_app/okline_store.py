"""Account-scoped directory, explicit MID binding and durable text delivery journal."""
import hashlib
import json
import time
import uuid
import threading

from .group_replies import should_reply_in_group


MEDIA_NAMES = {1: '圖片', 2: '影片', 3: '語音', 7: '貼圖', 14: '檔案'}


def message_content(message):
    kind = int(message.get('contentType') or 0)
    if kind == 0:
        return str(message.get('text') or '').strip()
    return '[' + MEDIA_NAMES.get(kind, '非文字訊息') + ']'


class LineStore:
    def __init__(self, repo):
        self.repo = repo
        self.account = ''
        self.since = 0
        self._payloads = {}
        self._guard = threading.RLock()
        with repo.database.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS line_contacts (
                    account TEXT NOT NULL, mid TEXT NOT NULL, name TEXT NOT NULL,
                    alias TEXT NOT NULL DEFAULT '', original_name TEXT NOT NULL DEFAULT '',
                    avatar_url TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL DEFAULT 'person', blocked INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(account,mid));
                CREATE TABLE IF NOT EXISTS line_cursor(account TEXT PRIMARY KEY, revision INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS line_sent(account TEXT NOT NULL,id TEXT NOT NULL,PRIMARY KEY(account,id));
                CREATE TABLE IF NOT EXISTS line_inbox (
                    account TEXT NOT NULL,id TEXT NOT NULL,target_id TEXT NOT NULL,
                    raw TEXT NOT NULL,status TEXT NOT NULL,receipt TEXT NOT NULL DEFAULT '',
                    incoming_id INTEGER,error TEXT NOT NULL DEFAULT '',created INTEGER NOT NULL,
                    PRIMARY KEY(account,id));
            """)
            # A newly constructed store has no live work. Finalize interrupted
            # journals for every account before a stopped app can retain them.
            db.execute("DELETE FROM line_inbox WHERE target_id NOT IN (SELECT id FROM targets)")
            accounts=[r[0] for r in db.execute("SELECT DISTINCT account FROM line_inbox WHERE status IN ('pending','processing','sending','context')")]
        for account in accounts:
            self.account=account
            self.recover()
        self.account=''

    @property
    def scope(self):
        return self.account

    def activate(self, account):
        with self._guard:
            if self.account != str(account):
                self.archive_pending()
            self.account = str(account)

    def refresh_contacts(self, contacts):
        if not self.scope:
            raise ValueError('line_login_required')
        with self.repo.database.connect() as db:
            db.execute('UPDATE line_contacts SET blocked=1 WHERE account=?', (self.scope,))
            for c in contacts:
                if not isinstance(c.get('id'), str) or not c['id'] or c.get('kind', 'person') not in {'person', 'group'}:
                    continue
                db.execute("""INSERT INTO line_contacts VALUES(?,?,?,?,?,?,?,?)
                    ON CONFLICT(account,mid) DO UPDATE SET name=excluded.name,alias=excluded.alias,
                    original_name=excluded.original_name,avatar_url=excluded.avatar_url,kind=excluded.kind,blocked=excluded.blocked""",
                    (self.scope,c['id'],c['name'],c.get('alias',''),c.get('originalName',c['name']),c.get('avatarUrl',''),c.get('kind','person'),int(c['blocked'])))
                # Binding remains stable across display-name changes, including ended targets.
                db.execute('UPDATE targets SET name=?,line_kind=? WHERE line_account=? AND line_mid=?', (c['name'],c.get('kind','person'),self.scope,c['id']))

    def contacts(self):
        with self.repo.database.connect() as db:
            return [dict(r) for r in db.execute("""SELECT c.mid AS id,c.name,c.alias,c.original_name AS originalName,
                c.avatar_url AS avatarUrl,c.kind,c.blocked,t.id AS targetId FROM line_contacts c
                LEFT JOIN targets t ON t.line_account=c.account AND t.line_mid=c.mid
                WHERE c.account=? ORDER BY c.name,c.mid""", (self.scope,))]

    def contact(self, mid):
        c = next((c for c in self.contacts() if c['id']==mid), None)
        if not c or c['blocked'] or not isinstance(mid, str) or not mid:
            raise ValueError('line_contact_unavailable')
        return c

    def bind(self, target_id, mid):
        c = self.contact(mid)
        target = self.repo.get_target(target_id)
        if target.get('line_mid'):
            if target['line_account']==self.scope and target['line_mid']==mid:
                return target
            raise ValueError('line_target_already_bound')
        with self.repo.database.connect() as db:
            if db.execute('SELECT 1 FROM targets WHERE line_account=? AND line_mid=?', (self.scope,mid)).fetchone():
                raise ValueError('line_contact_already_selected')
            key = 'line:' + hashlib.sha256((self.scope+mid).encode()).hexdigest()
            db.execute('UPDATE targets SET name=?,name_key=?,line_account=?,line_mid=?,line_since=?,line_kind=? WHERE id=?',
                       (c['name'],key,self.scope,mid,int(time.time()*1000),c.get('kind','person'),target_id))
        return self.repo.get_target(target_id)

    def add(self, mid, assignment):
        self.contact(mid)
        with self.repo.database.connect():
            # Temporary internal name avoids the legacy unique display-name index.
            t = self.repo.create_target({**assignment,'name':'pending-'+uuid.uuid4().hex,'reply_enabled':False})
            return self.bind(t['id'],mid)

    def targets(self):
        contacts = {c['id']:c for c in self.contacts()}
        return [t for t in self.repo.list_monitor_targets()
                if self.scope and t.get('line_account')==self.scope and t.get('line_mid') in contacts
                and not contacts[t['line_mid']]['blocked']]

    def cursor(self):
        with self.repo.database.connect() as db:
            row=db.execute('SELECT revision FROM line_cursor WHERE account=?',(self.scope,)).fetchone()
        return row['revision'] if row else None

    def advance(self, revision):
        if revision is None or not self.scope:
            return
        with self.repo.database.connect() as db:
            db.execute('INSERT INTO line_cursor VALUES(?,?) ON CONFLICT(account) DO UPDATE SET revision=max(revision,excluded.revision)',(self.scope,int(revision)))

    def ingest(self, message, revision=None, *, context_only=False):
        with self._guard, self.repo.database.connect() as db:
            self.advance(revision)
            if not self.scope or not message.get('id'):
                return False
            outgoing=message.get('from')==self.account
            group=int(message.get('toType') or 0)!=0
            peer=message.get('to') if outgoing or group else message.get('from')
            target=next((t for t in self.targets() if t.get('line_mid')==peer),None)
            stamp=int(message.get('createdTime') or 0)
            if not target or stamp<target.get('line_since',0):
                return False
            if db.execute('SELECT 1 FROM line_sent WHERE account=? AND id=?',(self.scope,str(message['id']))).fetchone():
                return False
            group_trigger = not group or should_reply_in_group(message, self.account, self.repo.get_settings().get('user_names', ''))
            eligible=(group_trigger and not context_only and not outgoing and target['status']=='active' and target['reply_enabled']
                      and stamp>=self.since and int(message.get('contentType') or 0) in (0,1,7) and message_content(message))
            inserted=bool(db.execute('INSERT OR IGNORE INTO line_inbox(account,id,target_id,raw,status,created) VALUES(?,?,?,?,?,?)',
                (self.scope,str(message['id']),target['id'],'{}','pending' if eligible else 'archived',stamp)).rowcount)
            if inserted and eligible:
                self._payloads[(self.scope,str(message["id"]))] = dict(message)
            return inserted

    def rows(self, statuses=('pending',)):
        marks=','.join('?' for _ in statuses)
        with self._guard, self.repo.database.connect() as db:
            result=[]
            for r in db.execute(f'SELECT * FROM line_inbox WHERE account=? AND status IN ({marks}) ORDER BY created,rowid',(self.scope,*statuses)):
                payload=self._payloads.get((self.scope,r['id']))
                if payload is not None:
                    result.append({**dict(r),'raw':json.dumps(payload,ensure_ascii=False)})
            return result

    def row(self, mid):
        with self.repo.database.connect() as db:
            r=db.execute('SELECT * FROM line_inbox WHERE account=? AND id=?',(self.scope,mid)).fetchone()
        return dict(r) if r else None

    def update(self, mid, status, *, receipt='', error=''):
        with self._guard, self.repo.database.connect() as db:
            db.execute('UPDATE line_inbox SET status=?,receipt=?,error=? WHERE account=? AND id=?',(status,receipt,error,self.scope,mid))
            if status in ('sent','archived','failed','uncertain'):
                self._payloads.pop((self.scope,mid),None)

    def recover(self):
        with self._guard, self.repo.database.connect() as db:
            db.execute("UPDATE line_inbox SET status='uncertain',error='interrupted_during_send' WHERE account=? AND status='sending'",(self.scope,))
            self.archive_pending()

    def archive_pending(self):
        with self._guard, self.repo.database.connect() as db:
            db.execute("UPDATE line_inbox SET status='archived' WHERE account=? AND status IN ('pending','processing','context')",(self.scope,))
            self._payloads={key:value for key,value in self._payloads.items() if key[0]!=self.scope}

    def complete(self, rows, receipt):
        with self._guard, self.repo.database.connect() as db:
            if db.execute('SELECT 1 FROM line_sent WHERE account=? AND id=?',(self.scope,receipt)).fetchone():
                return
            self.repo.record_reply(rows[0]['target_id'])
            db.execute('INSERT INTO line_sent VALUES(?,?)',(self.scope,receipt))
            for row in rows:
                self.update(row['id'],'sent',receipt=receipt)
