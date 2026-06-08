"""Plot grid-workload benchmark latencies (Vexor vs Python) on log-log axes.

Reads two wide-format CSVs (no header): column 1 is the grid size N, columns 2..31
are 30 independent latency runs (ms). The workload scale is N*N (total elements).
Latency is shown in microseconds so the log-decade ticks land on clean values.
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

# Engine -> source CSV (wide format, no header: N + 30 run columns).
SOURCES = {
    "Vexor": os.path.join(DATA, "vexor-grid.csv"),
    "Python": os.path.join(DATA, "ph-grid.csv"),
}
OUTPUT_SVG = os.path.join(PLOTS, "grid_benchmark_loglog.svg")

METRIC = "N"
RUNS = 30
PALETTE = {"Vexor": "#4C72B0", "Python": "#C44E52"}
LATENCY = "Latency (µs)"


def load_long(path, engine):
    """Load one wide CSV and melt the 30 run columns into long form (µs)."""
    run_cols = [f"run_{i}" for i in range(RUNS)]
    df = pd.read_csv(path, header=None, names=[METRIC] + run_cols)
    long = df.melt(
        id_vars=METRIC,
        value_vars=run_cols,
        var_name="Run",
        value_name=LATENCY,
    )
    long[LATENCY] = long[LATENCY] * 1000.0  # ms -> µs
    # Workload scale: total visual geometry elements = N * N.
    long["Total Elements"] = long[METRIC] * long[METRIC]
    long["Engine"] = engine
    return long


def build_dataset():
    """Combine all engines into a single long-form dataframe with an Engine hue."""
    return pd.concat(
        [load_long(path, engine) for engine, path in SOURCES.items()],
        ignore_index=True,
    )


def apply_style():
    """Clean, high-contrast academic theme with serif typography."""
    sns.set_theme(style="whitegrid")
    plt.rcParams["font.family"] = "serif"


def plain_scalar():
    """A ScalarFormatter that prints plain integers (no scientific/offset)."""
    fmt = ScalarFormatter()
    fmt.set_scientific(False)
    fmt.set_useOffset(False)
    return fmt


def plot(df):
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.lineplot(
        data=df,
        x="Total Elements",
        y=LATENCY,
        hue="Engine",
        palette=PALETTE,
        marker="o",
        estimator="median",
        errorbar=("pi", 90),
        err_style="bars",
        err_kws={"capsize": 4, "capthick": 1.2, "elinewidth": 1.2},
        ax=ax,
    )

    # Log-log axes with explicit scalar element counts on x; plain decade labels on y.
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(sorted(df["Total Elements"].unique()))
    ax.xaxis.set_major_formatter(plain_scalar())
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_major_formatter(plain_scalar())
    ax.yaxis.set_minor_formatter(NullFormatter())

    ax.set_xlabel("Total Visual Geometry Elements (N²)")
    ax.set_ylabel("Round-Trip Latency (µs)")
    ax.set_title("Grid Workload: Rebuild Latency vs Geometry Count (log-log)")
    ax.legend(title="Engine")

    fig.savefig(OUTPUT_SVG, format="svg", bbox_inches="tight")
    print(f"Wrote {OUTPUT_SVG}")


def main():
    apply_style()
    plot(build_dataset())


if __name__ == "__main__":
    main()
