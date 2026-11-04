import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path

DB=Path('studylens_demo.db')
def connection():
    con=sqlite3.connect(str(DB),timeout=20)
    con.execute('PRAGMA busy_timeout=20000')
    return con

def init():
    with connection() as c:
        c.execute('CREATE TABLE IF NOT EXISTS answers (id INTEGER PRIMARY KEY, demo_id TEXT, assessment TEXT, created TEXT, payload TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS revision (demo_id TEXT, topic TEXT, status TEXT, updated TEXT, PRIMARY KEY (demo_id,topic))')
        c.execute('CREATE TABLE IF NOT EXISTS flashcards (id TEXT PRIMARY KEY, demo_id TEXT, topic TEXT, front TEXT, back TEXT, due TEXT, interval_days INTEGER DEFAULT 1)')

def save_attempt(demo_id,rows):
    assessment=str(uuid.uuid4())
    with connection() as c:
        c.executemany('INSERT INTO answers (demo_id,assessment,created,payload) VALUES (?,?,?,?)',[(demo_id,assessment,datetime.now().isoformat(timespec='seconds'),json.dumps(r)) for r in rows])
    return assessment

def attempts(demo_id):
    with connection() as c: records=c.execute('SELECT assessment,created,payload FROM answers WHERE demo_id=? ORDER BY id',(demo_id,)).fetchall()
    return [dict(assessment=a,created=dt,**json.loads(p)) for a,dt,p in records]

def revision_set(demo_id,topic,status):
    with connection() as c:c.execute('INSERT INTO revision VALUES(?,?,?,?) ON CONFLICT(demo_id,topic) DO UPDATE SET status=excluded.status,updated=excluded.updated',(demo_id,topic,status,datetime.now().isoformat(timespec='seconds')))

def revision_get(demo_id):
    with connection() as c:return c.execute('SELECT topic,status,updated FROM revision WHERE demo_id=? ORDER BY updated DESC',(demo_id,)).fetchall()

def card_add(demo_id,topic,front,back):
    with connection() as c:c.execute('INSERT INTO flashcards(id,demo_id,topic,front,back,due,interval_days) VALUES(?,?,?,?,?,date("now"),1)',(str(uuid.uuid4()),demo_id,topic,front,back))

def card_get(demo_id):
    with connection() as c:return c.execute('SELECT id,topic,front,back,due,interval_days FROM flashcards WHERE demo_id=? ORDER BY due',(demo_id,)).fetchall()

def card_review(card_id,known):
    with connection() as c:
        old=c.execute('SELECT interval_days FROM flashcards WHERE id=?',(card_id,)).fetchone()
        if not old:return
        days=min(60,max(1,int(old[0])*2)) if known else 1
        c.execute('UPDATE flashcards SET interval_days=?,due=date("now", ? ) WHERE id=?',(days,f'+{days} days',card_id))
