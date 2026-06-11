"""Benchmark every toolchain's rebuild latency across complexity cases.

TOOLCHAINS lists each toolchain (python harness, vexor) and its designs. For each
design this auto-starts the toolchain's watcher subprocess (writing to a temp svg),
then for each case rewrites the first line of INPUT to set the complexity variable,
runs `vx-time multi N INPUT OUTPUT`, and records the N round-trip latencies (comma-
separated ms). Rows go to data/{tool}-{name}.csv. The watcher is torn down after.

No manual setup required -- watchers are launched and killed here. Pass toolchain
names as args to record only those, e.g. `record_benchmarks.py vexor` (default:
all).
"""

import csv
import os
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

HERE = os.path.dirname(os.path.abspath(__file__))  # benchmarks/scripts
ROOT = os.path.dirname(HERE)  # benchmarks
REPO = os.path.dirname(ROOT)  # repo root

N = 30
VX_TIME = os.path.join(REPO, "svg-timer", "target", "release", "vx-time")

SETTLE = 0.5  # seconds to let the warmup rebuild from a line edit settle
WARMUP = 10  # seconds to wait for the watcher's first output before measuring
TIMEOUT = 600  # per-case ceiling for vx-time multi

# --- python harness toolchain ---------------------------------------------
PY_DESIGN = os.path.join(REPO, "python", "design")
HARNESS = os.path.join(REPO, "python", "harness.py")
# harness.py needs watchdog + drawsvg -- run it with the repo-level venv if
# present, else whatever interpreter is running this script.
_VENV_PY = os.path.join(REPO, ".venv", "bin", "python")
PYTHON = _VENV_PY if os.path.exists(_VENV_PY) else sys.executable


def ph_watch(input_path, output_path):
    """harness.py doesn't chdir, so the design's relative `open("name.svg")`
    writes into the process cwd -- point it at the temp dir holding output_path."""
    return [PYTHON, HARNESS, input_path], os.path.dirname(output_path)


# --- vexor toolchain ------------------------------------------------------
VX_DESIGN = os.path.join(REPO, "vexor", "design")


def vexor_watch(input_path, output_path):
    """vexor takes an explicit OUTPUT arg."""
    return ["vexor", "watch", input_path, output_path], None


TOOLCHAINS = [
    {
        "tool": "python",  # csv prefix: data/python-{name}.csv
        "watch_command": ph_watch,
        "first_line": lambda var, case: f"{var} = {case}\n",
        "tests": [
            {
                "name": "grid",
                "input": os.path.join(PY_DESIGN, "grid.py"),
                "cases": [5, 10, 16, 27, 50],
                "var_name": "N",
            },
            {
                "name": "fractal",
                "input": os.path.join(PY_DESIGN, "fractal.py"),
                "cases": [1, 2, 3, 4, 5, 6, 7, 8],
                "var_name": "D",
            },
        ],
    },
    {
        "tool": "vexor",  # csv prefix: data/vexor-{name}.csv
        "watch_command": vexor_watch,
        "first_line": lambda var, case: f"val {var} = {case}\n",
        "tests": [
            {
                "name": "grid",
                "input": os.path.join(VX_DESIGN, "grid.vx"),
                "cases": [5, 10, 16, 27, 50],
                "var_name": "N",
            },
            {
                "name": "fractal",
                "input": os.path.join(VX_DESIGN, "fractal.vx"),
                "cases": [1, 2, 3, 4, 5, 6, 7, 8],
                "var_name": "D",
            },
        ],
    },
]


def set_case(toolchain, test, case):
    with open(test["input"]) as f:
        lines = f.readlines()
    lines[0] = toolchain["first_line"](test["var_name"], case)
    with open(test["input"], "w") as f:
        f.writelines(lines)


def run_case(test, output):
    proc = subprocess.run(
        [VX_TIME, "multi", str(N), test["input"], output],
        capture_output=True,
        text=True,
        check=True,
        timeout=TIMEOUT,
    )
    values = proc.stdout.strip().split(",")
    if len(values) != N:
        raise RuntimeError(f"expected {N} values, got {len(values)}: {proc.stdout!r}")
    return values


def run_test(toolchain, test):
    csv_path = os.path.join(ROOT, "data", f"{toolchain['tool']}-{test['name']}.csv")
    with TemporaryDirectory() as tmp:
        output = os.path.join(tmp, Path(test["input"]).stem + ".svg")
        argv, cwd = toolchain["watch_command"](test["input"], output)
        proc = subprocess.Popen(
            argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        try:
            deadline = time.monotonic() + WARMUP
            while not os.path.exists(output):
                if proc.poll() is not None:
                    sys.exit(
                        f"watcher exited early for {test['name']}: "
                        f"{proc.stderr.read().strip()}"
                    )
                if time.monotonic() > deadline:
                    sys.exit(f"no output from watcher for {test['name']} ({output})")
                time.sleep(0.1)

            rows = []
            for case in test["cases"]:
                set_case(toolchain, test, case)
                time.sleep(SETTLE)
                try:
                    values = run_case(test, output)
                except subprocess.TimeoutExpired:
                    sys.exit(f"timeout on {test['name']} {test['var_name']}={case}")
                except subprocess.CalledProcessError as e:
                    sys.exit(
                        f"vx-time failed on {test['name']} "
                        f"{test['var_name']}={case}: {e.stderr.strip()}"
                    )
                print(
                    f"{toolchain['tool']} {test['name']} {test['var_name']}={case}: "
                    f"{values[0]} .. {values[-1]} ms ({N} samples)"
                )
                rows.append([case, *values])
        finally:
            proc.terminate()
            proc.wait()

    with open(csv_path, "w", newline="") as f:
        csv.writer(f).writerows(rows)
    print(f"Wrote {csv_path} ({len(rows)} rows)")


def main():
    names = sys.argv[1:]
    valid = {t["tool"] for t in TOOLCHAINS}
    unknown = [n for n in names if n not in valid]
    if unknown:
        sys.exit(f"unknown toolchain(s) {unknown}; valid: {sorted(valid)}")

    for toolchain in TOOLCHAINS:
        if names and toolchain["tool"] not in names:
            continue
        for test in toolchain["tests"]:
            run_test(toolchain, test)


if __name__ == "__main__":
    main()
