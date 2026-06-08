"""Benchmark the python-harness toolchain's rebuild latency across complexity cases.

For each case D in CASES this rewrites the first line of INPUT to `D = {case}`, then
runs `vx-time multi N INPUT OUTPUT` and records the N round-trip latencies the tool
prints (comma-separated ms). All rows are written to ph.csv.

A `python harness.py INPUT` process must already be running (with DEBOUNCE_SECONDS = 0)
so the harness re-execs the design and regenerates OUTPUT on each save -- otherwise
vx-time blocks until timeout.
"""

import csv
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))  # benchmarks/scripts
ROOT = os.path.dirname(HERE)  # benchmarks
REPO = os.path.dirname(ROOT)  # repo root

# INPUT = os.path.join(REPO, "python-harness", "design", "fractal.py")
# OUTPUT = os.path.join(REPO, "python-harness", "design", "fractal.svg")
# CASES = [1, 2, 3, 4, 5, 6, 7, 8]
# VAR_NAME = "D"
INPUT = os.path.join(REPO, "python-harness", "design", "grid.py")
OUTPUT = os.path.join(REPO, "python-harness", "design", "grid.svg")
CASES = [5, 10, 16, 27, 50]
VAR_NAME = "N"

N = 30
VX_TIME = os.path.join(REPO, "benchmarker", "target", "release", "vx-time")
CSV = os.path.join(ROOT, "data", "ph.csv")

SETTLE = 0.5  # seconds to let the warmup rebuild finish before measuring
TIMEOUT = 600  # per-case ceiling for vx-time multi


def first_line(case):
    return f"{VAR_NAME} = {case}\n"


def set_case(case):
    with open(INPUT) as f:
        lines = f.readlines()
    lines[0] = first_line(case)
    with open(INPUT, "w") as f:
        f.writelines(lines)


def run_case(case):
    set_case(case)
    time.sleep(SETTLE)  # warmup rebuild from the line edit settles
    proc = subprocess.run(
        [VX_TIME, "multi", str(N), INPUT, OUTPUT],
        capture_output=True,
        text=True,
        check=True,
        timeout=TIMEOUT,
    )
    values = proc.stdout.strip().split(",")
    if len(values) != N:
        raise RuntimeError(f"expected {N} values, got {len(values)}: {proc.stdout!r}")
    return values


def main():
    rows = []
    for case in CASES:
        try:
            values = run_case(case)
        except subprocess.TimeoutExpired:
            sys.exit(
                f"timeout on case D={case}. Is `python harness.py {INPUT}` running?"
            )
        except subprocess.CalledProcessError as e:
            sys.exit(f"vx-time failed on case D={case}: {e.stderr.strip()}")
        print(f"D={case}: {values[0]} .. {values[-1]} ms ({N} samples)")
        rows.append([case, *values])

    with open(CSV, "w", newline="") as f:
        csv.writer(f).writerows(rows)
    print(f"Wrote {CSV} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
