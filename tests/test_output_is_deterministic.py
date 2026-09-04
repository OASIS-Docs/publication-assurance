"""The same package must produce the same report every time it is checked.

Nine finding loops iterated a `set()` directly, so under Python's per-process
hash randomisation the order of the findings changed between runs of identical
code on identical input. Six runs against one corpus package produced two
different outputs. TC Administration files these reports as the record of a
publication, and a TC diffing two runs saw churn that meant nothing.

`PUB_CHECK_OFFLINE` is set so the live-site checks cannot introduce a real
difference between runs and mask, or fake, this one.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from conftest import CORPUS, PUB_CHECK

PACKAGES = [
    "csaf/v2.1/csd01",
    "csaf/v2.0/csd01",
    "csaf-cvrf/v1.2/cs01",
]


def _run(package):
    env = dict(os.environ, PUB_CHECK_OFFLINE="1")
    # A fresh interpreter per run: hash randomisation is per process, and two
    # runs inside one process would share the seed and hide the defect.
    return subprocess.run([sys.executable, str(PUB_CHECK), str(CORPUS / package)],
                          capture_output=True, text=True, env=env).stdout


@pytest.mark.parametrize("package", PACKAGES)
def test_repeated_runs_produce_identical_output(package):
    runs = {_run(package) for _ in range(6)}
    assert len(runs) == 1, (
        f"{package} produced {len(runs)} different reports in six runs; the "
        f"findings must come out in a stable order.")
    assert runs.pop().strip(), f"{package} produced no output at all"
