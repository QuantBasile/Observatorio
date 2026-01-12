from __future__ import annotations

import pandas as pd
import numpy as np

def _require_df(df: pd.DataFrame | None, name: str):
    if df is None or df.empty:
        raise ValueError(f"{name} dataframe is empty. Load it first.")


def run(raptor: pd.DataFrame) -> pd.DataFrame:
    _require_df(raptor, "Raptor")
    if "Issuer" not in raptor.columns or "currency" not in raptor.columns:
        return action_1(raptor)
    g = raptor.groupby(["Issuer", "currency"], observed=True)
    if "spread_bps" in raptor.columns:
        out = g["spread_bps"].agg(count="count", mean="mean", p95=lambda s: float(np.nanpercentile(pd.to_numeric(s, errors="coerce"), 95)))
    else:
        out = g.size().to_frame("count")
    return out.reset_index()
