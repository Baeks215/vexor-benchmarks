"""Plot fractal-workload benchmark latencies (Vexor vs Python) as a publication SVG.

Reads two wide-format CSVs (no header): column 1 is the recursion depth D, columns
2..31 are 30 independent latency runs (ms). The workload scale is 3**D (total elements).
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

# Engine -> source CSV (wide format, no header: D + 30 run columns).
SOURCES = {
    "Vexor": os.path.join(DATA, "vexor-fractal.csv"),
    "Python": os.path.join(DATA, "ph-fractal.csv"),
}
OUTPUT_SVG = os.path.join(PLOTS, "fractal_benchmark.svg")

METRIC = "D"
RUNS = 30
PALETTE = {"Vexor": "#4C72B0", "Python": "#C44E52"}


def load_long(path, engine):
    """Load one wide CSV and melt the 30 run columns into long form."""
    run_cols = [f"run_{i}" for i in range(RUNS)]
    df = pd.read_csv(path, header=None, names=[METRIC] + run_cols)
    long = df.melt(
        id_vars=METRIC,
        value_vars=run_cols,
        var_name="Run",
        value_name="Latency (ms)",
    )
    # Workload scale: total visual geometry elements = 3 ** D.
    long["Total Elements"] = 3 ** long[METRIC]
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


def force_scalar_ticks(ax, ticks):
    """Show explicit scalar element counts on the log x-axis (e.g. 3, 9, 27, 2187)."""
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
        y="Latency (ms)",
        hue="Engine",
        palette=PALETTE,
        marker="o",
        estimator="median",
        errorbar=("pi", 90),
        err_style="bars",
        err_kws={"capsize": 4, "capthick": 1.2, "elinewidth": 1.2},
        ax=ax,
    )

    ax.set_xscale("log")
    force_scalar_ticks(ax, sorted(df["Total Elements"].unique()))

    ax.set_xlabel("Total Visual Geometry Elements (3ᴰ)")
    ax.set_ylabel("Round-Trip Latency (ms)")
    ax.set_title("Fractal Workload: Rebuild Latency vs Geometry Count")
    ax.legend(title="Engine")

    fig.savefig(OUTPUT_SVG, format="svg", bbox_inches="tight")
    print(f"Wrote {OUTPUT_SVG}")


def main():
    apply_style()
    plot(build_dataset())


if __name__ == "__main__":
    main()
