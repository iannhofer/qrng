# QRNG — Quantum Random Number Generator

Generates random bits and stores then in a database alongside other data later used for analysis.

## How it works

Creates a Hadamard Gate and collapses it by measuring. The resulting bits are stored in a MySQL database and then used for analysis (random bit generation speed, min-entropy).


## Requirements

- Python 3.10+
- IBM Quantum account, API token
- Packages: `qiskit`, `qiskit-ibm-runtime`, `python-dotenv`, `numpy`

## Setup

```bash

python -m venv .venv
source .venv/bin/activate

pip install qiskit qiskit-ibm-runtime python-dotenv numpy
```

Copy the example environment file and add your IBM Quantum API token:

```bash
cp .env.example .env
```

```dotenv
# .env
IBM_KEY = your_ibm_quantum_api_token
```

`.env` is git-ignored, so your token stays out of version control.

## Usage

Generate a batch of bits (defaults to 10,000) and store them:

```bash
python main.py
```

Or use the API directly:

```python
import qrng
import analysis

# generate and store a batch; returns the number of bits stored
qrng.generateBits(n=10000)

# generate a single bit without storing it
bit = qrng.generateBit()

# analyse a stored session
print(analysis.calcMinEntropy(session_id=1))  # bits of min-entropy per bit
print(analysis.calcSpeed(session_id=1))        # bits per second on the QPU
```

> **Note:** running against real hardware submits a job to the IBM Quantum queue.
> Jobs may wait before executing depending on backend demand.

## Project structure

| File          | Purpose                                              |
| ------------- | ---------------------------------------------------- |
| `main.py`     | Entry point — generates a batch of bits.             |
| `qrng.py`     | Quantum circuit and IBM Runtime job submission.      |
| `db.py`       | SQLite storage for sessions and bits.                |
| `analysis.py` | Quality metrics over stored bits.                    |
| `qrng.db`     | Local SQLite database (created on first run).        |

## Data model

A **session** is one run/batch of bit generation.

- `sessions` — one row per batch: `source` (e.g. `hadamard`) and `exec_time`
  (official IBM QPU execution time in seconds, excluding queue wait).
- `bits` — one row per generated bit, linked to its session via `session_id`.

## Analysis

- **Min-entropy** (`calcMinEntropy`) — `-log2(p_max)`, where `p_max` is the
  frequency of the most common bit value. Quantifies worst-case predictability;
  ideal random bits approach 1.0 bit of min-entropy per bit.
- **Generation speed** (`calcSpeed`) — bits divided by the QPU execution time,
  in bits per second.
