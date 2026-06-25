import os
import random
import time
from datetime import datetime
from math import pi

import numpy as np
import qiskit
from qiskit import transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit_aer import AerSimulator
from dotenv import load_dotenv
from qiskit_ibm_runtime.base_runtime_job import BaseRuntimeJob


def _fake_start_websocket_client(self):
    pass
BaseRuntimeJob._start_websocket_client = _fake_start_websocket_client

import db
from analysis import performCHSH


load_dotenv()
if "IBM_KEY" in os.environ and os.environ["IBM_KEY"]:
    QiskitRuntimeService.save_account(
        token=os.environ["IBM_KEY"],
        instance=os.environ.get("IBM_INSTANCE"),
        overwrite=True
    )


# measuremnet settings for self testing
CHSH_BASES = {
    "A0B0": (0.0, pi / 4),
    "A0B1": (0.0, 3 * pi / 4),
    "A1B0": (pi / 2, pi / 4),
    "A1B1": (pi / 2, 3 * pi / 4),
}


# circuit: hadamard gate in superposition, measure
def _genCircuit():
    qc = qiskit.QuantumCircuit(1, 1)
    qc.h(0)
    qc.measure(0, 0)
    return qc


# returns circuit: bell pair, with each qubit measured at a different angle (specified in parameter), then measured
def _auditCircuit(theta_a: float, theta_b: float):
    qc = qiskit.QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.ry(theta_a, 0)
    qc.ry(theta_b, 1)
    qc.measure([0, 1], [0, 1])
    return qc


# sums the execution-span durations attributable to one pub (circuit) in milliseconds.
def _pubDuration(job_result) -> float:
    try:
        if 'execution' in job_result.metadata:
            execution_spans = job_result.metadata['execution']['execution_spans']
            # Get the first span and calculate duration
            span = execution_spans[0]
            start = datetime.fromisoformat(str(span.start))
            stop = datetime.fromisoformat(str(span.stop))
            duration_ms = (stop - start).total_seconds() * 1000
            return duration_ms
            
        if isinstance(job_result.metadata, dict):
            if 'time_taken' in job_result.metadata:
                return float(job_result.metadata['time_taken']) * 1000
            elif 'execution_time' in job_result.metadata:
                return float(job_result.metadata['execution_time']) * 1000

        if isinstance(job_result.metadata, list) or isinstance(job_result.metadata, tuple):
            if len(job_result.metadata) > 0:
                if 'time_taken' in job_result.metadata[0]:
                    return float(job_result.metadata[0]['time_taken']) * 1000
                elif 'execution_time' in job_result.metadata[0]:
                    return float(job_result.metadata[0]['execution_time']) * 1000
        return 0.0
    except (KeyError, AttributeError, IndexError, TypeError, ValueError) as e:
        return 0.0


# gets job duration from ibm
def _getJobDuration(job, job_result) -> float:
    duration_ms = _pubDuration(job_result)
    if duration_ms > 0.0:
        return duration_ms

    for attempt in range(5):
        try:
            metrics = job.metrics()
            if metrics and 'timestamps' in metrics:
                running_str = metrics['timestamps'].get('running')
                finished_str = metrics['timestamps'].get('finished')
                if running_str and finished_str:
                    r_dt = datetime.fromisoformat(running_str.replace('Z', '+00:00'))
                    f_dt = datetime.fromisoformat(finished_str.replace('Z', '+00:00'))
                    duration_ms = (f_dt - r_dt).total_seconds() * 1000
                    if duration_ms > 0.0:
                        return duration_ms
            
            usage = metrics.get('usage', {})
            seconds = usage.get('seconds') or usage.get('quantum_seconds')
            if seconds:
                return float(seconds) * 1000
        except Exception:
            pass
        
        if attempt < 4:
            time.sleep(2)

    return 0.0


# takes 8 bits, returns a byte
def generateByte(bits) -> int:
    byte = 0
    for b in bits:
        byte = (byte << 1) | (int(b) & 1)
    return byte

def _extract_bitarray(pub_result):
    if isinstance(pub_result, dict):
        if '__value__' in pub_result:
            data_obj = pub_result['__value__'].get('data', pub_result['__value__'])
        else:
            data_obj = pub_result.get('data', pub_result)
    else:
        data_obj = pub_result.data

    if isinstance(data_obj, dict):
        bitarray = data_obj.get('c')
        if bitarray is None:
            bitarray = list(data_obj.values())[0]
    else:
        if hasattr(data_obj, 'c'):
            bitarray = data_obj.c
        else:
            fields = getattr(data_obj, '_fields', None)
            if fields:
                bitarray = getattr(data_obj, fields[0])
            else:
                bitarray = None
    return bitarray


# generates quantum random numbers
def generateBatch(n_bytes: int = 200, use_simulator: bool = False) -> int:
    circuit = _genCircuit()
    n_bits = n_bytes * 8
    gen_time = 0.0

    if use_simulator:
        from qiskit_aer.primitives import SamplerV2 as AerSampler
        sampler = AerSampler()
        start_time = time.time()
        job = sampler.run([circuit], shots=n_bits)
        result = job.result()
        gen_time = (time.time() - start_time) * 1000  # Wall-clock timing in ms
        pub_result = result[0]
        bitarray = _extract_bitarray(pub_result)
        gen_bits = [int(b) for b in bitarray.get_bitstrings()]
    else:
        service = QiskitRuntimeService()
        backend = service.least_busy(operational=True, simulator=False)
        
        transpiled_circuit = transpile(circuit, backend=backend)
        
        sampler = Sampler(backend=backend)
        job = sampler.run([transpiled_circuit], shots=n_bits)
        result = job.result()
        gen_time = _getJobDuration(job, result)
        pub_result = result[0]
        bitarray = _extract_bitarray(pub_result)
        gen_bits = [int(b) for b in bitarray.get_bitstrings()]

    usable_bits = len(gen_bits) - (len(gen_bits) % 8)
    gen_bytes = [generateByte(gen_bits[i:i + 8]) for i in range(0, usable_bits, 8)]

    session_id = db.storeSession("qrng-simple", gen_time, None, is_simulation=use_simulator)
    db.storeBytes(gen_bytes, session_id)
    return session_id

# generates quantum random numbers and performs chsh/bell test
def generateVerifiedBatch(n_bytes: int = 4, use_simulator: bool = False) -> int:

    bases = list(CHSH_BASES.items())
    n_bits = n_bytes * 8
    
    gen_bits = []
    audit_rows_temp = {}
    total_time = 0.0

    circuits = []
    chosen_bases = []
    for _ in range(n_bits):
        basis_name, (theta_a, theta_b) = random.choice(bases)
        chosen_bases.append(basis_name)
        circuits.append(_auditCircuit(theta_a, theta_b))

    if use_simulator:
        from qiskit_aer.primitives import SamplerV2 as AerSampler
        sampler = AerSampler()
        start_time = time.time()
        job = sampler.run(circuits, shots=1)
        result = job.result()
        total_time = (time.time() - start_time) * 1000  # Wall-clock timing in ms
        pub_results = result
    else:
        service = QiskitRuntimeService()
        backend = service.least_busy(operational=True, simulator=False)
        
        transpiled_circuits = transpile(circuits, backend=backend)
        
        sampler = Sampler(backend=backend)
        
        job = sampler.run(transpiled_circuits, shots=1)
        result = job.result()
        
        total_time = _getJobDuration(job, result)
        pub_results = result

    for i in range(n_bits):
        basis_name = chosen_bases[i]
        pub_result = pub_results[i]
        bitarray = _extract_bitarray(pub_result)
        bitstring = bitarray.get_bitstrings()[0]
        outcome = int(bitstring, 2)
        alice_bit = int(bitstring[1])
        gen_bits.append(alice_bit)
        key = (basis_name, outcome)
        audit_rows_temp[key] = audit_rows_temp.get(key, 0) + 1

    audit_rows = [(basis, outcome, count) for (basis, outcome), count in audit_rows_temp.items()]
    gen_bytes = [generateByte(gen_bits[i:i + 8]) for i in range(0, n_bits, 8)]

    chsh_score = performCHSH(audit_rows)

    session_id = db.storeSession("qrng-verified", total_time, None, chsh_score, is_simulation=use_simulator)
    db.storeBytes(gen_bytes, session_id)
    db.storeAudit(audit_rows, session_id)
    
    return session_id
