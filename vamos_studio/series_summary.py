"""The quality indicators of the runs of a series, and their summary statistics.

Pure pandas, no Streamlit.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

STATISTICS = ("median", "IQR", "mean", "std", "min", "max")


def indicator_table(rows: Sequence[tuple[int, str, Mapping[str, float]]]) -> pd.DataFrame:
    """One row per run: its seed, its identifier and the value of each indicator."""
    return pd.DataFrame([{"Seed": seed, "Run": run_id, **values} for seed, run_id, values in rows])


def summarize(table: pd.DataFrame, indicators: Sequence[str]) -> pd.DataFrame:
    """The median, interquartile range, mean, standard deviation, minimum and maximum of each."""
    columns = table[list(indicators)]
    summary = pd.DataFrame(
        {
            "median": columns.median(),
            "IQR": columns.quantile(0.75) - columns.quantile(0.25),
            "mean": columns.mean(),
            "std": columns.std(ddof=1) if len(columns) > 1 else 0.0,
            "min": columns.min(),
            "max": columns.max(),
        }
    )
    summary.index.name = "Indicator"
    return summary.reset_index()


def best_run(table: pd.DataFrame, indicator: str, maximized: bool) -> str:
    """The run with the best value of an indicator."""
    position = table[indicator].idxmax() if maximized else table[indicator].idxmin()
    return str(table.loc[position, "Run"])
