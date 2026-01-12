from __future__ import annotations

import pandas as pd
import numpy as np

def _require_df(df: pd.DataFrame | None, name: str):
    if df is None or df.empty:
        raise ValueError(f"{name} dataframe is empty. Load it first.")


def run(raptor: pd.DataFrame) -> pd.DataFrame:
    _require_df(raptor, "Raptor")
    cols = [c for c in ["Issuer", "Type", "OptionType"] if c in raptor.columns]
    if not cols:
        numeric = raptor.select_dtypes(include="number")
        return numeric.describe().T.reset_index().rename(columns={"index": "metric"})

    numeric_cols = raptor.select_dtypes(include="number").columns.tolist()
    use = [c for c in ["volume_1d", "open_interest", "spread_bps", "iv_30d", "px_last"] if c in numeric_cols] or numeric_cols[:6]
    agg = raptor.groupby(cols, observed=True)[use].agg(["count", "mean", "sum"])
    agg.columns = ["_".join([a, b]) for a, b in agg.columns.to_flat_index()]
    return agg.reset_index()
