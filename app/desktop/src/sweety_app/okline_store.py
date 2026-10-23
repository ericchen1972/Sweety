"""Account-scoped directory, explicit MID binding and durable text delivery journal."""
import hashlib
import json
import time
import uuid

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

    @property
    def scope(self):
        return self.account

    def activate(self, account):
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
        with self.repo.database.connect() as db:
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
                (self.scope,str(message['id']),target['id'],json.dumps(message,ensure_ascii=False),'pending' if eligible else 'context',stamp)).rowcount)
            return inserted

    def rows(self, statuses=('pending','context')):
        marks=','.join('?' for _ in statuses)
        with self.repo.database.connect() as db:
            return [dict(r) for r in db.execute(f'SELECT * FROM line_inbox WHERE account=? AND status IN ({marks}) ORDER BY created,rowid',(self.scope,*statuses))]

    def row(self, mid):
        with self.repo.database.connect() as db:
            r=db.execute('SELECT * FROM line_inbox WHERE account=? AND id=?',(self.scope,mid)).fetchone()
        return dict(r) if r else None

    def update(self, mid, status, *, receipt='', error=''):
        with self.repo.database.connect() as db:
            db.execute('UPDATE line_inbox SET status=?,receipt=?,error=? WHERE account=? AND id=?',(status,receipt,error,self.scope,mid))

    def archive(self, row):
        """Save real input once, without incrementing completed-reply statistics."""
        with self.repo.database.connect() as db:
            current=self.row(row['id'])
            if not current or current['incoming_id']:
                return current['incoming_id'] if current else None
            raw=json.loads(row['raw']);content=message_content(raw)
            if int(raw.get('toType') or 0)!=0:
                content=f"[{raw.get('from', '?')}] {content}"
            if not content:
                return None
            role='assistant' if raw.get('from')==self.account else 'scammer'
            cursor=db.execute('INSERT INTO messages(target_id,role,content,created_at) VALUES(?,?,?,?)',
                             (row['target_id'],role,content,time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(row['created']/1000))))
            db.execute('UPDATE line_inbox SET incoming_id=? WHERE account=? AND id=?',(cursor.lastrowid,self.scope,row['id']))
            return cursor.lastrowid

    def describe_media(self, rows, descriptions):
        by_id={item.message_id:item.description for item in descriptions}
        with self.repo.database.connect() as db:
            for row in rows:
                if row['id'] not in by_id:
                    continue
                raw=json.loads(row['raw'])
                kind=int(raw.get('contentType') or 0)
                if kind not in (1,7):
                    continue
                content=('貼圖' if kind==7 else '圖片')+'辨識：'+by_id[row['id']]
                if int(raw.get('toType') or 0)!=0:
                    content=f"[{raw.get('from','?')}] {content}"
                db.execute('UPDATE messages SET content=? WHERE id=? AND target_id=?',
                           (content,row['incoming_id'],row['target_id']))

    def recover(self):
        with self.repo.database.connect() as db:
            db.execute("UPDATE line_inbox SET status='uncertain',error='interrupted_during_send' WHERE account=? AND status='sending'",(self.scope,))
            db.execute("UPDATE line_inbox SET status='context' WHERE account=? AND status IN ('pending','processing')",(self.scope,))

    def archive_pending(self):
        with self.repo.database.connect() as db:
            db.execute("UPDATE line_inbox SET status='context' WHERE account=? AND status IN ('pending','processing')",(self.scope,))

    def complete(self, rows, reply, receipt):
        with self.repo.database.connect() as db:
            if db.execute('SELECT 1 FROM line_sent WHERE account=? AND id=?',(self.scope,receipt)).fetchone():
                return
            self.repo.add_message(rows[0]['target_id'],'assistant',reply)
            db.execute('INSERT INTO line_sent VALUES(?,?)',(self.scope,receipt))
            for row in rows:
                self.update(row['id'],'sent',receipt=receipt)
