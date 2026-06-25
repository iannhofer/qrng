import math
from collections import Counter, defaultdict
from typing import List, Tuple

from db import getBytes, getDuration, getAuditDataForSessions, countBytes, getSessionIDsBySource


# get min-entropy of a seqence of bits
def calcMinEntropy(bits=None, session_id=None):
    if bits is None:
        bits = getBytes(session_id)

    n = len(bits)
    if n == 0:
        return 0.0

    counts = Counter(bits)
    max_prob = max(counts.values()) / n
    return -math.log2(max_prob)

# returns bits per seconds for a session
def calcSpeed(session_id):
    num_bytes = len(getBytes(session_id))
    exec_time = getDuration(session_id)

    if num_bytes == 0 or not exec_time:
        return 0.0

    return (num_bytes * 8) / (exec_time / 1000)

# calculates chsh score
def performCHSH(audit_rows: List[Tuple[str, int, int]]) -> float:
    basis_counts = defaultdict(lambda: defaultdict(int))
    for basis, outcome, count in audit_rows:
        basis_counts[basis][outcome] += count

    expectations = {}
    for basis, counts in basis_counts.items():
        total_shots = sum(counts.values())
        if total_shots == 0:
            expectations[basis] = 0.0
            continue

        p00 = counts.get(0, 0) / total_shots
        p01 = counts.get(1, 0) / total_shots
        p10 = counts.get(2, 0) / total_shots
        p11 = counts.get(3, 0) / total_shots
        
        correlation = p00 - p01 - p10 + p11
        expectations[basis] = correlation

    s_value = (
        expectations.get("A0B0", 0.0)
        - expectations.get("A0B1", 0.0)
        + expectations.get("A1B0", 0.0)
        + expectations.get("A1B1", 0.0)
    )

    return s_value

# calculate chsh score for multiple sessions (with data from db)
def performCHSHForSessions(session_ids: List[int]) -> float:
    if not session_ids:
        return 0.0
    
    combined_audit_rows = getAuditDataForSessions(session_ids)
    
    return performCHSH(combined_audit_rows)

# calculate byte generation speed
def calcSpeedForSessions(session_ids: List[int]) -> float:
    if not session_ids:
        return 0.0

    total_bytes = 0
    total_duration_ms = 0

    for session_id in session_ids:
        duration = getDuration(session_id)
        if duration and duration > 0.0:
            total_bytes += countBytes(session_id)
            total_duration_ms += duration

    if total_bytes == 0 or not total_duration_ms:
        return 0.0

    return (total_bytes * 8) / (total_duration_ms / 1000)

# prints a summary of metrics calculated from all db data
def report_all_metrics():
    print("--- Generator Performance Report ---")

    print("\nGeneration Speed (bits/sec):")
    
    prng_ids = getSessionIDsBySource("prng")
    trng_ids = getSessionIDsBySource("trng")
    qrng_simple_ids = getSessionIDsBySource("qrng-simple", simulated=False)
    qrng_verified_ids = getSessionIDsBySource("qrng-verified", simulated=False)

    prng_speed = calcSpeedForSessions(prng_ids)
    trng_speed = calcSpeedForSessions(trng_ids)
    qrng_simple_speed = calcSpeedForSessions(qrng_simple_ids)
    qrng_verified_speed = calcSpeedForSessions(qrng_verified_ids)

    print(f"  - PRNG (Mersenne Twister): {prng_speed:,.2f} bits/sec")
    print(f"  - TRNG (Atmospheric Noise): {trng_speed:,.2f} bits/sec")
    print(f"  - QRNG (Simple Hadamard): {qrng_simple_speed:,.2f} bits/sec")
    print(f"  - QRNG (Self-Testing): {qrng_verified_speed:,.2f} bits/sec")

    print("\nQuantum Verification:")
    
    qrng_verified_sim = getSessionIDsBySource("qrng-verified", simulated=True)
    qrng_verified_real = getSessionIDsBySource("qrng-verified", simulated=False)
    qrng_verified_all = qrng_verified_sim + qrng_verified_real
    
    if not qrng_verified_all:
        print("  - No self-testing sessions found to analyze.")
    else:
        chsh_score = performCHSHForSessions(qrng_verified_all)
        print(f"  - Combined CHSH Score: {chsh_score:.4f}")
        print(f"  - Expected quantum value: ~2.828 (2√2)")
        print(f"  - Classical limit: 2.0")
        if chsh_score > 2.0:
            print("  - Result: VIOLATES Bell's inequality (Quantum Behavior Confirmed)")
        else:
            print("  - Result: DOES NOT violate Bell's inequality (Quantum Behavior Not Confirmed)")

    print("\n--- End of Report ---")
