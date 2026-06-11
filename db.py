import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "qrng.db")

# create db for storing bits
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bits (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            bit      INTEGER NOT NULL,
            consumed INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    return conn


# stores bits in db
def storeBits(bits):
    conn = _connect()
    with conn:
        conn.executemany("INSERT INTO bits (bit) VALUES (?)", [(int(b),) for b in bits])
    conn.close()


