from __future__ import annotations

import pandas as pd
import numpy as np

def _require_df(df: pd.DataFrame | None, name: str):
    if df is None or df.empty:
        raise ValueError(f"{name} dataframe is empty. Load it first.")


def run(raptor: pd.DataFrame) -> pd.DataFrame:
    _require_df(raptor, "Raptor")
    if "delta" not in raptor.columns:
        return action_2(raptor)
    out = raptor.assign(abs_delta=pd.to_numeric(raptor["delta"], errors="coerce").abs())
    out = out.sort_values("abs_delta", ascending=False, na_position="last").head(800)
    cols = [c for c in ["scheme_id", "Issuer", "Type", "OptionType", "Bid", "Ask", "delta", "abs_delta", "iv_30d"] if c in out.columns]
    if cols:
        out = out[cols]
    return out.reset_index(drop=True)
