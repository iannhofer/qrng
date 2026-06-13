import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "qrng.db")


# creates session and bit table. session is one run/batch of retrieving bits.
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            source     TEXT NOT NULL,
            exec_time  REAL
        );

        CREATE TABLE IF NOT EXISTS bits (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            bit        INTEGER NOT NULL,
            session_id INTEGER NOT NULL REFERENCES sessions(id)
        );
        """
    )

#stores session, how bits were generated and duration
def storeSession(source, exec_time):
    conn = _connect()
    with conn:
        cur = conn.execute(
            "insert into sessions (source, exec_time) values (?,?)",
            (source, exec_time),
        )
        session_id=cur.lastrowid
    conn.close()
    return session_id


# returns execution time of a session (excludes ibm queue)
def getDuration(session_id):
    conn = _connect()
    with conn:
        row = conn.execute(
            "SELECT exec_time FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    conn.close()
    return row[0] if row else None


# stores bits in db under the given session
def storeBits(bits, session_id):
    conn = _connect()
    with conn:
        conn.executemany(
            "INSERT INTO bits (bit, session_id) VALUES (?, ?)",
            [(int(b), session_id) for b in bits],
        )
    conn.close()


# returns bits ordered by id, can be filtered by session
def getBits(session_id=None):
    conn = _connect()
    with conn:
        if session_id is None:
            rows = conn.execute("SELECT bit FROM bits ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                "SELECT bit FROM bits WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
    conn.close()
    return [row[0] for row in rows]

# returns number of bits generated in a session
def countBits(session_id):
    conn = _connect()
    with conn:
        row = conn.execute(
            "select count(*) from bits where session_id = ?",
            (session_id,),
        ).fetchone()
    conn.close()
    return row[0]