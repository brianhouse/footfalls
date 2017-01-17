#!/usr/bin/env python3

import sqlite3, json, os
from housepy import config, log

def db_call(f):
    def wrapper(*args, desc=False):
        connection = sqlite3.connect(os.path.abspath(os.path.join(os.path.dirname(__file__), "data.db")))
        connection.row_factory = sqlite3.Row
        db = connection.cursor()
        results = f(db, *args)
        connection.commit()
        connection.close()
        return results
    return wrapper

@db_call
def init(db):
    try:
        db.execute("CREATE TABLE walks (id INTEGER PRIMARY KEY, start_time INTEGER, duration INTEGER, ref_id INTEGER)")
        db.execute("CREATE TABLE geo_data (walk_id INTEGER, t INTEGER, lat REAL, lng REAL)")
        db.execute("CREATE INDEX geo_data_walk_id ON geo_data(walk_id)")
        db.execute("CREATE TABLE accel_data (walk_id INTEGER, t INTEGER, x REAL, y REAL, z REAL)")
        db.execute("CREATE INDEX accel_data_walk_id ON accel_data(walk_id)")
        db.execute("CREATE TABLE sequence (walk_id INTEGER, t INTEGER, foot TEXT)")
        db.execute("CREATE INDEX sequence_walk_id ON sequence(walk_id)")
    except Exception as e:
        if hasattr(e, 'message'):
            e = e.message
        if "already exists" not in str(e):
            raise e
init()

@db_call
def insert_walk(db, walk):
    try:
        db.execute("INSERT INTO walks (start_time, duration, ref_id) VALUES (?, ?, ?)", (walk['start_time'], walk['duration'], walk['ref_id']))
        walk_id = db.lastrowid    
        for gd in walk['geo_data']:
            db.execute("INSERT INTO geo_data (walk_id, t, lat, lng) VALUES (?, ?, ?, ?)", (walk_id, gd[0], gd[1], gd[2]))
        for ad in walk['accel_data']:
            db.execute("INSERT INTO accel_data (walk_id, t, x, y, z) VALUES (?, ?, ?, ?, ?)", (walk_id, ad[0], ad[1], ad[2], ad[3]))
    except Exception as e:
        log.error(log.exc(e))
        return None
    return walk_id

@db_call
def insert_sequence(db, walk_id, sequence):
    try:
        for step in sequence:
            db.execute("INSERT INTO sequence (walk_id, t, foot) VALUES (?, ?, ?)", (walk_id, int(step[0]), step[1]))
    except Exception as e:
        log.error(log.exc(e))
        return None

@db_call
def fetch_walks(db, desc=False):
    try:
        db.execute("SELECT * FROM walks WHERE duration > 10000 ORDER BY start_time %s" % ("DESC" if desc else ""))
        rows = [dict(gd) for gd in db.fetchall()]
    except Exception as e:
        log.error(log.exc(e))
        rows = []
    return rows    

@db_call
def fetch_geo(db, walk_id):
    db.execute("SELECT * FROM geo_data WHERE walk_id=?", (walk_id,))
    rows = [dict(gd) for gd in db.fetchall()]
    return rows

@db_call
def fetch_sequence(db, walk_id=None):    
    if walk_id is None:
        db.execute("SELECT id FROM walks ORDER BY start_time DESC LIMIT 1")
        walk = db.fetchone()
        walk_id = walk['id'] if walk is not None else 1
    db.execute("SELECT * FROM sequence WHERE walk_id=?", (walk_id,))        
    results = db.fetchall()
    sequence = [(step['t'], step['foot']) for step in results]
    if len(results):
        log.info("--> fetching sequence from walk %s" % results[0]['walk_id'])
    else:
        log.info("--> no data retrieved for walk %s" % walk_id)
    return sequence

@db_call
def fetch_accels(db, walk_id):
    db.execute("SELECT * FROM accel_data WHERE walk_id=?", (walk_id,))
    rows = [dict(reading) for reading in db.fetchall()]
    return rows

@db_call
def process_check(db, walk_id):
    db.execute("SELECT * FROM sequence WHERE walk_id=?", (walk_id,))
    return len(db.fetchall()) == 0

@db_call
def remove_sequence(db, walk_id):
    db.execute("DELETE FROM sequence WHERE walk_id=?", (walk_id,))
