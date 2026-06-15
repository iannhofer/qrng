import random
import time

import db


# generates pseudo random bits, times duration and stores the data in the db
def generateBits(n = 10000):
    start = time.perf_counter_ns()
    bits = [random.getrandbits(1) for _ in range(n)]
    exec_time = (time.perf_counter_ns() - start) / 1e6  # generation time, in ms

    session_id = db.storeSession("prng", exec_time)
    db.storeBits(bits, session_id)
    return len(bits)
