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
            start_time TEXT,
            end_time   TEXT
        );

        CREATE TABLE IF NOT EXISTS bits (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            bit        INTEGER NOT NULL,
            session_id INTEGER NOT NULL REFERENCES sessions(id)
        );
        """
    )
    return conn

# return time now
def now():
    return datetime.now(timezone.utc).isoformat()


# stores start time of session, returns session id
def startSession(source):
    conn = _connect()
    with conn:
        cur = conn.execute(
            "INSERT INTO sessions (source, start_time) VALUES (?, ?)",
            (source, now()),
        )
        session_id = cur.lastrowid
    conn.close()
    return session_id

# stores end time of session
def endSession(session_id):
    conn = _connect()
    with conn:
        conn.execute(
            "UPDATE sessions SET end_time = ? WHERE id = ?",
            (now(), session_id),
        )
    conn.close()


# stores bits in db under the given session
def storeBits(bits, session_id):
    conn = _connect()
    with conn:
        conn.executemany(
            "INSERT INTO bits (bit, session_id) VALUES (?, ?)",
            [(int(b), session_id) for b in bits],
        )
    conn.close()


# returns bits ordered by id, optionally filter by session
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
