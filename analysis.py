import math
from collections import Counter

from db import getBits


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
