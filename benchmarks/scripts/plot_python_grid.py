"""Plot the Python grid-workload latency on its own (narrative figure).

Reads one wide-format CSV (no header): column 1 is the grid size N, columns 2..31 are
30 independent latency runs (ms). The workload scale is N*N (total elements).
"""

import os

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.ticker import NullFormatter, ScalarFormatter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # benchmarks
DATA = os.path.join(ROOT, "data")
PLOTS = os.path.join(ROOT, "plots")

SOURCE = os.path.join(DATA, "python-grid.csv")
OUTPUT_SVG = os.path.join(PLOTS, "python_grid_benchmark.svg")

METRIC = "N"
RUNS = 30
COLOR = "#C44E52"  # Python series colour, matching the combined plots


def load_long(path):
    """Load the wide CSV and melt the 30 run columns into long form."""
    run_cols = [f"run_{i}" for i in range(RUNS)]
    df = pd.read_csv(path, header=None, names=[METRIC] + run_cols)
    long = df.melt(
        id_vars=METRIC,
        value_vars=run_cols,
        var_name="Run",
        value_name="Execution Time (ms)",
    )
    # Workload scale: total visual geometry elements = N * N.
    long["Total Elements"] = long[METRIC] * long[METRIC]
    long["Engine"] = "Python"
    return long


def apply_style():
    """Clean, high-contrast academic theme with serif typography."""
    sns.set_theme(style="whitegrid")
    plt.rcParams["font.family"] = "serif"


def force_scalar_ticks(ax, ticks):
    """Show explicit scalar element counts on the log x-axis (e.g. 25, 100, 2500)."""
    fmt = ScalarFormatter()
    fmt.set_scientific(False)
    fmt.set_useOffset(False)
    ax.set_xticks(ticks)
    ax.xaxis.set_major_formatter(fmt)
    ax.xaxis.set_minor_formatter(NullFormatter())


def plot(df):
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.lineplot(
        data=df,
        x="Total Elements",
        y="Execution Time (ms)",
        color=COLOR,
        marker="o",
        estimator="median",
        errorbar=("pi", 90),
        err_style="bars",
        err_kws={"capsize": 4, "capthick": 1.2, "elinewidth": 1.2},
        ax=ax,
    )

    ax.set_xscale("log")
    force_scalar_ticks(ax, sorted(df["Total Elements"].unique()))

    ax.set_xlabel("Total Visual Geometry Elements (N²)")
    ax.set_ylabel("Execution Time (ms)")
    ax.set_title("Python Grid Workload: Rebuild Execution Time vs Geometry Count")

    fig.savefig(OUTPUT_SVG, format="svg", bbox_inches="tight")
    print(f"Wrote {OUTPUT_SVG}")


def main():
    apply_style()
    plot(load_long(SOURCE))


if __name__ == "__main__":
    main()
