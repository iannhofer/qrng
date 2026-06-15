import os
from math import pi

import qiskit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from dotenv import load_dotenv

import db


load_dotenv()
QiskitRuntimeService.save_account(token = os.environ["IBM_KEY"], overwrite=True)


# the four CHSH measurement settings: (Alice angle, Bob angle), in radians.
# chosen so an ideal Bell pair gives S = E[A0B0] - E[A0B1] + E[A1B0] + E[A1B1] = 2*sqrt(2).
CHSH_BASES = {
    "A0B0": (0.0, pi / 4),
    "A0B1": (0.0, 3 * pi / 4),
    "A1B0": (pi / 2, pi / 4),
    "A1B1": (pi / 2, 3 * pi / 4),
}


# GEN circuit: one qubit in superposition via a hadamard gate, then measured.
# its measurements are the random output.
def _genCircuit() -> qiskit.QuantumCircuit:
    qc = qiskit.QuantumCircuit(1, 1)
    qc.h(0)
    qc.measure(0, 0)
    return qc


# AUDIT circuit: a Bell pair measured at the given Alice/Bob angles. its
# measurements are CHSH evidence, never used as output.
def _auditCircuit(theta_a: float, theta_b: float) -> qiskit.QuantumCircuit:
    qc = qiskit.QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.ry(-2 * theta_a, 0)
    qc.ry(-2 * theta_b, 1)
    qc.measure([0, 1], [0, 1])
    return qc


# sums the execution-span durations attributable to one pub (circuit), in seconds.
def _pubDuration(spans, pub_idx: int) -> float:
    total = 0.0
    for span in spans:
        if pub_idx in span.data_slices:
            d = span.duration
            total += d.total_seconds() if hasattr(d, "total_seconds") else d
    return total


# assembles one byte from 8 measured bits, MSB-first.
def generateByte(bits) -> int:
    byte = 0
    for b in bits:
        byte = (byte << 1) | (int(b) & 1)
    return byte


# generates one random (50/50) bit and returns it, without storing.
def generateBit() -> int:
    service = QiskitRuntimeService()
    backend = service.least_busy(operational = True, simulator = False)
    pm = generate_preset_pass_manager(optimization_level = 1, backend = backend)
    sampler = SamplerV2(mode = backend)

    result = sampler.run([(pm.run(_genCircuit()), None, 1)]).result()
    bits = result[0].data.c.get_bitstrings()
    return int(bits[0])


# verification duty cycle: submits the GEN circuit and the four AUDIT circuits
# in one job so the CHSH audit is contemporaneous with generation. stores the
# packed output bytes, the raw audit tallies and per-type timing as one session.
def generateBatch(n: int = 10000, audit_shots: int = 4096) -> int:
    bases = list(CHSH_BASES.items())

    service = QiskitRuntimeService()
    backend = service.least_busy(operational = True, simulator = False)
    pm = generate_preset_pass_manager(optimization_level = 1, backend = backend)

    isa_gen = pm.run(_genCircuit())
    isa_audits = [pm.run(_auditCircuit(a, b)) for _, (a, b) in bases]

    sampler = SamplerV2(mode = backend)
    pubs = [(isa_gen, None, n)] + [(c, None, audit_shots) for c in isa_audits]
    job = sampler.run(pubs)
    result = job.result()

    # GEN output -> bytes, assembled one byte at a time from the measured bits
    gen_bits = [int(b) for b in result[0].data.c.get_bitstrings()]
    usable = len(gen_bits) - (len(gen_bits) % 8)
    gen_bytes = [generateByte(gen_bits[i:i + 8]) for i in range(0, usable, 8)]

    # AUDIT evidence -> (basis, outcome, count) tallies
    audit_rows = []
    for idx, (basis, _) in enumerate(bases, start = 1):
        counts = result[idx].data.c.get_counts()
        for bitstring, count in counts.items():
            audit_rows.append((basis, int(bitstring, 2), count))

    # split the measured QPU wall-clock per circuit type, in ms
    spans = result.metadata["execution"]["execution_spans"]
    gen_time = _pubDuration(spans, 0) * 1000
    audit_time = sum(_pubDuration(spans, i) for i in range(1, len(pubs))) * 1000

    session_id = db.storeSession("qrng", gen_time, audit_time)
    db.storeBytes(gen_bytes, session_id)
    db.storeAudit(audit_rows, session_id)
    return session_id
