# Description

This prototype generates random numbers using PRNG, TRNG, trusted QRNG and self-testing QRNG and also tracks their respective generation speed to show the fundamental tradeoff between security and speed.


## Setup

clone repo: 
git clone https://github.com/iannhofer/qrng.git

create venv:
python -m venv .venv
source .venv/bin/activate

install dependencies:
pip install -r requirements.txt

optional (if you want to generate quantum random numbers yourself)
put your ibm quantum api token into the .env, as well as the instance


# Usage

use PRNG:
python -c "import prng; prng.generateBatch(n_bytes=2048)"
(adjust bytes)

use TRNG: 
python -c "import trng; trng.generateBatch(n_bytes=512)"

use trusted QRNG, simulated:
python -c "import qrng; qrng.generateBatch(n_bytes=16, use_simulator=True)"


use trusted QRNG, real quantum hardware:
python -c "import qrng; qrng.generateBatch(n_bytes=16, use_simulator=False)"


use DI-QRNG, simlated:
python -c "import qrng; qrng.generateVerifiedBatch(n_bytes=4, use_simulator=True)"


use DI-QRNG, real quantum hardware:
python -c "import qrng; qrng.generateVerifiedBatch(n_bytes=4, use_simulator=False)"


get report/metrics:
python -c "import analysis; analysis.report_all_metrics()"

