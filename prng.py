import random
import time
import os
from typing import Tuple, List

import db
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator


# generates bits with a prng
def generateBits(n=10000):
    start = time.perf_counter_ns()
    bits = [random.getrandbits(1) for _ in range(n)]
    exec_time = (time.perf_counter_ns() - start) / 1e6  # generation time, in ms

    session_id = db.storeSession("prng", exec_time)
    db.storeBits(bits, session_id)
    return len(bits)
