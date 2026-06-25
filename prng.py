import random
import time
import db

# generates pseudo random numbers
def generateBatch(n_bytes: int = 8192) -> int:
    n_bits = n_bytes * 8
    
    start_time = time.perf_counter_ns()
    
    # Generate a list of random bits
    bits = [random.getrandbits(1) for _ in range(n_bits)]
    
    exec_time_ms = (time.perf_counter_ns() - start_time) / 1e6

    byte_values = bytearray()
    for i in range(0, n_bits, 8):
        byte = 0
        for j in range(8):
            byte |= (bits[i + j] << (7 - j))
        byte_values.append(byte)

    # Store the session and data
    session_id = db.storeSession("prng", exec_time_ms)
    db.storeBytes(bytes(byte_values), session_id)

    return session_id
