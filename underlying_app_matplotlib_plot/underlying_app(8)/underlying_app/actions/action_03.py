from __future__ import annotations

import pandas as pd
import numpy as np

def _require_df(df: pd.DataFrame | None, name: str):
    if df is None or df.empty:
        raise ValueError(f"{name} dataframe is empty. Load it first.")


def run(raptor: pd.DataFrame) -> pd.DataFrame:
    _require_df(raptor, "Raptor")
    df = raptor
    rows = len(df)
    miss = df.isna().mean().rename("missing_frac").reset_index().rename(columns={"index": "column"})
    miss["missing_pct"] = (miss["missing_frac"] * 100).round(2)
    miss = miss.sort_values("missing_frac", ascending=False)
    dtypes = df.dtypes.astype(str).rename("dtype").reset_index().rename(columns={"index": "column"})
    out = miss.merge(dtypes, on="column", how="left")
    out.insert(0, "rows_total", rows)
    return out[["rows_total", "column", "dtype", "missing_pct", "missing_frac"]]
