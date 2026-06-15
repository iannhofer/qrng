import qiskit
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from qiskit.compiler import transpile
import os
from dotenv import load_dotenv

import db


load_dotenv()
QiskitRuntimeService.save_account(token = os.environ["IBM_KEY"], overwrite=True)

#generates one random (50/50) bit by putting a qubit in superposition with a hadamard gate, then measuring
def generateBit():
    qc = qiskit.QuantumCircuit(1,1)
    qc.h(0)
    qc.measure(0,0)
    service = QiskitRuntimeService()
    backend = service.least_busy(operational = True, simulator = False)
    transpiled_qc = transpile(qc, backend)
    sampler = SamplerV2(mode = backend)

    result = sampler.run([transpiled_qc], shots = 1).result()
    bits = result[0].data.c.get_bitstrings()
    return int(bits[0])


# generates n bits and stores them in the db
def generateBits(n = 10000):
    qc = qiskit.QuantumCircuit(1,1)
    qc.h(0)
    qc.measure(0,0)

    service = QiskitRuntimeService()
    backend = service.least_busy(operational = True, simulator = False)
    transpiled_qc = transpile(qc, backend)
    sampler = SamplerV2(mode = backend)

    job = sampler.run([transpiled_qc], shots = n)
    result = job.result()
    bits = [int(b) for b in result[0].data.c.get_bitstrings()]
    spans = result.metadata["execution"]["execution_spans"]
    exec_time = spans.duration * 1000  # measured QPU wall-clock, in ms

    session_id = db.storeSession("hadamard", exec_time)
    db.storeBits(bits, session_id)
    return len(bits)