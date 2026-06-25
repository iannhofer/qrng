import time
import requests
import db

API_URL = "https://www.random.org/integers/"

# generates true random numbers (gets them from random.org)
def generateBatch(n_bytes: int = 1024) -> int:

    params = {
        "num": n_bytes,
        "min": 0,
        "max": 255,
        "col": 1,
        "base": 10,
        "format": "plain",
        "rnd": "new",
    }

    start_time = time.perf_counter_ns()
    
    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()  
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from random.org: {e}")
        return -1 

    exec_time_ms = (time.perf_counter_ns() - start_time) / 1e6

    byte_values = [int(line) for line in response.text.strip().splitlines()]

    session_id = db.storeSession("trng", exec_time_ms)
    db.storeBytes(bytes(byte_values), session_id)

    return session_id
