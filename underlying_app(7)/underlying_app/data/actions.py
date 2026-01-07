
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

import numpy as np
import pandas as pd


def _require_df(df: pd.DataFrame | None, name: str):
    if df is None or df.empty:
        raise ValueError(f"{name} dataframe is empty. Load it first.")


@dataclass(frozen=True)
class ActionSpec:
    key: str
    title: str
    button_text: str
    nav_text: str
    run: Callable[[pd.DataFrame], pd.DataFrame]
    row_limit: int = 2000
    enable_filters: bool = False  # per your request for actions: show table without filters


# --- Example actions (replace with your real logic later) ---

def action_1(raptor: pd.DataFrame) -> pd.DataFrame:
    """
    Example "Action 1": aggregate by issuer/type/currency.
    Produces a compact summary table.
    """
    _require_df(raptor, "Raptor")

    cols = [c for c in ["issuer", "type", "currency"] if c in raptor.columns]
    if not cols:
        numeric = raptor.select_dtypes(include="number")
        out = numeric.describe().T.reset_index().rename(columns={"index": "metric"})
        return out

    numeric_cols = raptor.select_dtypes(include="number").columns.tolist()
    use = [c for c in ["volume_1d", "open_interest", "spread_bps", "iv_30d", "px_last"] if c in numeric_cols]
    if not use:
        use = numeric_cols[:5]

    agg = raptor.groupby(cols, observed=True)[use].agg(["count", "mean", "sum"])
    agg.columns = ["_".join([a, b]) for a, b in agg.columns.to_flat_index()]
    return agg.reset_index()


def action_2(raptor: pd.DataFrame) -> pd.DataFrame:
    """
    Example "Action 2": top-N by open_interest (or first numeric col).
    Returns a manageable slice with useful columns.
    """
    _require_df(raptor, "Raptor")

    df = raptor
    sort_col = "open_interest" if "open_interest" in df.columns else None
    if sort_col is None:
        nums = df.select_dtypes(include="number").columns.tolist()
        sort_col = nums[0] if nums else None

    if sort_col is None:
        return df.head(100).reset_index(drop=True)

    out = df.sort_values(by=sort_col, ascending=False, na_position="last").head(500).copy()

    preferred = [c for c in ["scheme_id", "underlying_isin", "underlying_wkn", "issuer", "type", "currency", "maturity",
                             "strike", "barrier", "leverage", "px_last", "px_bid", "px_ask", "open_interest", "volume_1d",
                             "spread_bps", "iv_30d"] if c in out.columns]
    if len(preferred) >= 6:
        out = out[preferred]

    return out.reset_index(drop=True)


def action_3(raptor: pd.DataFrame) -> pd.DataFrame:
    """
    Example "Action 3": simple QA / missingness by column.
    """
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


def get_default_actions() -> list[ActionSpec]:
    """
    Register actions here. Add new actions by appending to this list.
    """
    return [
        ActionSpec(key="a1", title="Acción 1", button_text="Calculate 1", nav_text="Acción 1", run=action_1),
        ActionSpec(key="a2", title="Acción 2", button_text="Calculate 2", nav_text="Acción 2", run=action_2),
        ActionSpec(key="a3", title="Acción 3", button_text="Calculate 3", nav_text="Acción 3", run=action_3),
    ]
