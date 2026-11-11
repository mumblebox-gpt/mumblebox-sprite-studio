"""Atomic local persistence; feature owners decide lifecycle policy."""
import json
from pathlib import Path, PureWindowsPath
import sqlite3
import threading
import time


def safe_path(root, relative):
    relative = str(relative)
    if not relative or '\\' in relative or PureWindowsPath(relative).drive or Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('Only owned relative paths are accepted.')
    root = Path(root).resolve()
    target = (root/relative).resolve()
    if target==root or not target.is_relative_to(root):
        raise ValueError('Path must stay inside its owned directory.')
    return target


class StudioStore:
    def __init__(self, root):
        self.root = Path(root).resolve()
        if 'onedrive' in str(self.root).lower():
            raise ValueError('Studio data must use a local folder outside OneDrive.')
        self.root.mkdir(parents=True,exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.root/'studio.sqlite3',check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS documents(namespace TEXT,key TEXT,value TEXT NOT NULL,PRIMARY KEY(namespace,key));
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,request_id TEXT UNIQUE NOT NULL,recipe TEXT NOT NULL,
                created REAL NOT NULL,updated REAL NOT NULL,status TEXT NOT NULL,detail TEXT NOT NULL DEFAULT '{}',
                prompt_id TEXT,name TEXT NOT NULL DEFAULT '',favorite INTEGER NOT NULL DEFAULT 0,trashed INTEGER NOT NULL DEFAULT 0);
            CREATE INDEX IF NOT EXISTS runs_list ON runs(trashed,created DESC,id);
            CREATE INDEX IF NOT EXISTS runs_kind ON runs(trashed,json_extract(recipe,'$.kind'),created DESC,id);
            CREATE INDEX IF NOT EXISTS runs_favorite ON runs(trashed,favorite,created DESC,id);
            CREATE INDEX IF NOT EXISTS runs_status ON runs(status,created);
            CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY,filename TEXT UNIQUE NOT NULL,name TEXT NOT NULL,
                digest TEXT NOT NULL,width INTEGER NOT NULL,height INTEGER NOT NULL,created REAL NOT NULL);
        ''')
        self.db.commit()

    def close(self):
        with self.lock: self.db.close()

    def path(self, relative): return safe_path(self.root,relative)

    def put_document(self, namespace, key, value):
        payload = json.dumps(value,ensure_ascii=False,allow_nan=False)
        if len(payload)>1_000_000: raise ValueError('Saved settings are too large.')
        with self.lock,self.db:
            self.db.execute('INSERT INTO documents VALUES(?,?,?) ON CONFLICT(namespace,key) DO UPDATE SET value=excluded.value',(namespace,key,payload))

    def get_document(self, namespace, key, default=None):
        with self.lock: row=self.db.execute('SELECT value FROM documents WHERE namespace=? AND key=?',(namespace,key)).fetchone()
        return json.loads(row[0]) if row else default

    def create_run(self, run_id, recipe, request_id):
        now=time.time()
        with self.lock,self.db:
            self.db.execute('INSERT INTO runs(id,request_id,recipe,created,updated,status) VALUES(?,?,?,?,?,?)',
                (run_id,request_id,json.dumps(recipe,ensure_ascii=False,allow_nan=False),now,now,'preparing'))
        return self.get_run(run_id)

    @staticmethod
    def _run(row):
        if row is None: return None
        result=dict(row)
        result['recipe']=json.loads(result['recipe'])
        result['detail']=json.loads(result['detail'])
        return result

    def get_run(self, run_id):
        with self.lock: return self._run(self.db.execute('SELECT * FROM runs WHERE id=?',(run_id,)).fetchone())

    def by_request(self, request_id):
        with self.lock: return self._run(self.db.execute('SELECT * FROM runs WHERE request_id=?',(request_id,)).fetchone())

    def unfinished_runs(self):
        with self.lock:
            return [self._run(row) for row in self.db.execute("SELECT * FROM runs WHERE status IN ('preparing','downloading','ready','submitting','queued','running','recovering','canceling') ORDER BY created LIMIT 100")]

    def latest_completed(self, kind):
        with self.lock:
            return self._run(self.db.execute("SELECT * FROM runs WHERE status='completed' AND trashed=0 AND json_extract(recipe,'$.kind')=? ORDER BY created DESC LIMIT 1",(kind,)).fetchone())

    def update_run(self, run_id, status, detail=None, prompt_id=None, clear_prompt=False):
        with self.lock,self.db:
            self.db.execute('UPDATE runs SET status=?,detail=?,prompt_id=CASE WHEN ? THEN NULL ELSE COALESCE(?,prompt_id) END,updated=? WHERE id=?',
                (status,json.dumps(detail or {},ensure_ascii=False,allow_nan=False),clear_prompt,prompt_id,time.time(),run_id))

    def list_runs(self, limit=50, offset=0, sort='newest', kind=None, trashed=False, favorite=False):
        if not isinstance(limit,int) or not 1<=limit<=50 or not isinstance(offset,int) or not 0<=offset<=100000:
            raise ValueError('Use a page of 1–50 results.')
        if sort not in ('newest','oldest'): raise ValueError('Choose newest or oldest.')
        sql="SELECT * FROM runs WHERE trashed=? AND json_extract(recipe,'$.kind')!='enhance'"
        args=[int(trashed)]
        if favorite: sql+=' AND favorite=1'
        if kind:
            sql+=" AND json_extract(recipe,'$.kind')=?"
            args.append(kind)
        direction='DESC' if sort=='newest' else 'ASC'
        sql+=f' ORDER BY created {direction},id {direction} LIMIT ? OFFSET ?'
        with self.lock: return [self._run(row) for row in self.db.execute(sql,(*args,limit,offset))]

    def add_asset(self, asset):
        with self.lock,self.db:
            self.db.execute('INSERT INTO assets VALUES(?,?,?,?,?,?,?)',(asset['id'],asset['filename'],asset['name'],asset['digest'],asset['width'],asset['height'],time.time()))

    def get_asset(self, asset_id):
        with self.lock: row=self.db.execute('SELECT * FROM assets WHERE id=?',(asset_id,)).fetchone()
        if row is None: raise ValueError('Saved reference unavailable. Replace the reference card.')
        return dict(row)
