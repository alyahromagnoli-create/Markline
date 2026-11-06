"""Local SQLite state with validation, atomic imports and portable backups."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from core import credit_value,score_value

VERSION=1
SCHEMA='''
CREATE TABLE IF NOT EXISTS courses(
 id INTEGER PRIMARY KEY, term TEXT NOT NULL, name TEXT NOT NULL, code TEXT NOT NULL,
 credit TEXT NOT NULL, raw TEXT NOT NULL, score INTEGER, included INTEGER NOT NULL CHECK(included IN(0,1)),
 reason TEXT NOT NULL, UNIQUE(term,name,code));
CREATE TABLE IF NOT EXISTS peers(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS scenarios(id INTEGER PRIMARY KEY,name TEXT NOT NULL,payload TEXT NOT NULL,created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
'''

def validate(c):
    if not c['name'].strip(): raise ValueError('课程名不能为空')
    if c['included']:
        credit_value(c['credit']); score_value(c['score'])
        if c['score']!=score_value(c['raw']): raise ValueError('原始成绩与换算成绩不一致')
    elif not c['reason'].strip(): raise ValueError('排除课程请填写原因')

class Store:
    def __init__(self,path):
        self.path=Path(path).resolve(); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(self.path); self.conn.row_factory=sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys=ON')
        version=self.conn.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0,VERSION):
            self.conn.close(); raise ValueError('不支持该数据库版本，请使用匹配的软件版本')
        self.conn.executescript(SCHEMA); self.conn.execute(f'PRAGMA user_version={VERSION}'); self.conn.commit()

    def courses(self): return [dict(r) for r in self.conn.execute('SELECT * FROM courses ORDER BY id')]

    def put_course(self,c,identity=None):
        validate(c)
        keys=['term','name','code','credit','raw','score','included','reason']; vals=[c[k] for k in keys]
        with self.conn:
            if identity is None:
                return self.conn.execute('INSERT INTO courses('+','.join(keys)+') VALUES(?,?,?,?,?,?,?,?)',vals).lastrowid
            self.conn.execute('UPDATE courses SET '+','.join(k+'=?' for k in keys)+' WHERE id=?',vals+[identity])

    def delete_course(self,identity):
        with self.conn: self.conn.execute('DELETE FROM courses WHERE id=?',(identity,))

    def import_courses(self,courses):
        for c in courses: validate(c)
        added=updated=unchanged=0
        keys=['term','name','code','credit','raw','score','included','reason']
        with self.conn:
            for c in courses:
                old=self.conn.execute('SELECT * FROM courses WHERE term=? AND name=? AND code=?',tuple(c[k] for k in ['term','name','code'])).fetchone()
                values=[c[k] for k in keys]
                if old is None:
                    self.conn.execute('INSERT INTO courses('+','.join(keys)+') VALUES(?,?,?,?,?,?,?,?)',values); added+=1
                elif any(old[k]!=c[k] for k in keys):
                    self.conn.execute('UPDATE courses SET '+','.join(k+'=?' for k in keys)+' WHERE id=?',values+[old['id']]); updated+=1
                else: unchanged+=1
        return added,updated,unchanged

    def save_peer(self,name,payload,identity=None):
        if not name.strip(): raise ValueError('比较对象名称不能为空')
        data=json.dumps(payload,ensure_ascii=False)
        with self.conn:
            if identity:
                self.conn.execute('UPDATE peers SET name=?,payload=? WHERE id=?',(name,data,identity)); return identity
            return self.conn.execute('INSERT INTO peers(name,payload) VALUES(?,?)',(name,data)).lastrowid

    def peers(self): return [dict(r) for r in self.conn.execute('SELECT * FROM peers ORDER BY id')]

    def delete_peer(self,identity):
        with self.conn: self.conn.execute('DELETE FROM peers WHERE id=?',(identity,))

    def save_scenario(self,name,payload):
        if not name.strip(): raise ValueError('方案名称不能为空')
        with self.conn:
            return self.conn.execute('INSERT INTO scenarios(name,payload,created) VALUES(?,?,?)',
                (name,json.dumps(payload,ensure_ascii=False),datetime.now().isoformat(timespec='seconds'))).lastrowid

    def scenarios(self): return [dict(r) for r in self.conn.execute('SELECT id,name,created FROM scenarios ORDER BY id DESC')]
    def scenario(self,identity):
        r=self.conn.execute('SELECT payload FROM scenarios WHERE id=?',(identity,)).fetchone()
        if r is None: raise ValueError('方案不存在')
        return json.loads(r[0])
    def delete_scenario(self,identity):
        with self.conn: self.conn.execute('DELETE FROM scenarios WHERE id=?',(identity,))
    def setting(self,key,default=''):
        r=self.conn.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
        return r[0] if r else default
    def set_setting(self,key,value):
        with self.conn: self.conn.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(key,value))

    def backup(self,path):
        if Path(path).resolve()==self.path: raise ValueError('备份不能覆盖正在使用的数据文件')
        dest=sqlite3.connect(path)
        try: self.conn.backup(dest)
        finally: dest.close()

    def restore(self,path):
        path=Path(path).resolve()
        if path==self.path: raise ValueError('请选择备份文件，不要选择正在使用的数据文件')
        source=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True); source.row_factory=sqlite3.Row
        try:
            if source.execute('PRAGMA user_version').fetchone()[0]!=VERSION: raise ValueError('备份版本不受支持')
            if source.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('备份文件损坏')
            for row in source.execute('SELECT * FROM courses'): validate(dict(row))
            for table in ['peers','scenarios']:
                for row in source.execute(f'SELECT payload FROM {table}'): json.loads(row[0])
            source.execute('SELECT key,value FROM settings').fetchall()
            self.backup(self.path.with_name('before_restore_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.db'))
            source.backup(self.conn)
        finally: source.close()

    def close(self): self.conn.close()
