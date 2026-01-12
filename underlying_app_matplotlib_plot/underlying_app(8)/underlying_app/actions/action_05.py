from __future__ import annotations

import pandas as pd
import numpy as np

def _require_df(df: pd.DataFrame | None, name: str):
    if df is None or df.empty:
        raise ValueError(f"{name} dataframe is empty. Load it first.")


def run(raptor: pd.DataFrame) -> pd.DataFrame:
    _require_df(raptor, "Raptor")
    if "Maturity" not in raptor.columns:
        return action_1(raptor)
    m = pd.to_datetime(raptor["Maturity"], errors="coerce")
    days = (m - pd.Timestamp.now()).dt.days
    buckets = pd.cut(days, bins=[-10_000, 0, 7, 30, 90, 180, 365, 10_000], labels=["expired", "0-7d", "7-30d", "1-3m", "3-6m", "6-12m", "1y+"])
    df = raptor.copy()
    df["mat_bucket"] = buckets.astype("string")
    gcols = [c for c in ["Issuer", "mat_bucket"] if c in df.columns] or ["mat_bucket"]
    use = [c for c in ["open_interest", "volume_1d", "spread_bps"] if c in df.columns] or df.select_dtypes(include="number").columns.tolist()[:3]
    out = df.groupby(gcols, observed=True)[use].agg(["count", "mean"])
    out.columns = ["_".join([a, b]) for a, b in out.columns.to_flat_index()]
    return out.reset_index()
