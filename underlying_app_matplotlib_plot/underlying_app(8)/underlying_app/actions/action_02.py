from __future__ import annotations

import pandas as pd
import numpy as np

def _require_df(df: pd.DataFrame | None, name: str):
    if df is None or df.empty:
        raise ValueError(f"{name} dataframe is empty. Load it first.")


def run(raptor: pd.DataFrame) -> pd.DataFrame:
    _require_df(raptor, "Raptor")
    sort_col = "open_interest" if "open_interest" in raptor.columns else None
    if sort_col is None:
        nums = raptor.select_dtypes(include="number").columns.tolist()
        sort_col = nums[0] if nums else None
    if sort_col is None:
        return raptor.head(200).reset_index(drop=True)

    out = raptor.sort_values(by=sort_col, ascending=False, na_position="last").head(1000).copy()
    preferred = [c for c in ["scheme_id", "underlying_isin", "Issuer", "Type", "OptionType", "currency", "Maturity",
                             "Strike", "leverage", "Bid", "Ask", "px_last", "open_interest", "volume_1d", "spread_bps", "iv_30d"]
                 if c in out.columns]
    if len(preferred) >= 8:
        out = out[preferred]
    return out.reset_index(drop=True)
