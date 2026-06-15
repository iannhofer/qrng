import math
from collections import Counter

from db import getBits, getDuration


# get min-entropy of a seqence of bits
def calcMinEntropy(bits=None, session_id=None):
    if bits is None:
        bits = getBits(session_id)

    n = len(bits)
    if n == 0:
        return 0.0

    counts = Counter(bits)
    max_prob = max(counts.values()) / n
    return -math.log2(max_prob)

# returns bits per seconds for a session
def calcSpeed(session_id):
    bits = getBits(session_id)
    exec_time = getDuration(session_id)

    n = len(bits)
    if n == 0 or not exec_time:
        return 0.0

    return n / exec_time
