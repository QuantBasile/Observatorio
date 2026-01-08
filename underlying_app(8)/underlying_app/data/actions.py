
from __future__ import annotations

import numpy as np
import pandas as pd


def _require_df(df: pd.DataFrame | None, name: str):
    if df is None or df.empty:
        raise ValueError(f"{name} dataframe is empty. Load it first.")


def action_1(raptor: pd.DataFrame) -> pd.DataFrame:
    _require_df(raptor, "Raptor")
    cols = [c for c in ["issuer", "product", "callput"] if c in raptor.columns]
    if not cols:
        numeric = raptor.select_dtypes(include="number")
        return numeric.describe().T.reset_index().rename(columns={"index": "metric"})

    numeric_cols = raptor.select_dtypes(include="number").columns.tolist()
    use = [c for c in ["volume_1d", "open_interest", "spread_bps", "iv_30d", "px_last"] if c in numeric_cols] or numeric_cols[:6]
    agg = raptor.groupby(cols, observed=True)[use].agg(["count", "mean", "sum"])
    agg.columns = ["_".join([a, b]) for a, b in agg.columns.to_flat_index()]
    return agg.reset_index()


def action_2(raptor: pd.DataFrame) -> pd.DataFrame:
    _require_df(raptor, "Raptor")
    sort_col = "open_interest" if "open_interest" in raptor.columns else None
    if sort_col is None:
        nums = raptor.select_dtypes(include="number").columns.tolist()
        sort_col = nums[0] if nums else None
    if sort_col is None:
        return raptor.head(200).reset_index(drop=True)

    out = raptor.sort_values(by=sort_col, ascending=False, na_position="last").head(1000).copy()
    preferred = [c for c in ["scheme_id", "underlying_isin", "issuer", "product", "callput", "currency", "maturity",
                             "strike", "leverage", "Bid", "Ask", "px_last", "open_interest", "volume_1d", "spread_bps", "iv_30d"]
                 if c in out.columns]
    if len(preferred) >= 8:
        out = out[preferred]
    return out.reset_index(drop=True)


def action_3(raptor: pd.DataFrame) -> pd.DataFrame:
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


def action_4(raptor: pd.DataFrame) -> pd.DataFrame:
    _require_df(raptor, "Raptor")
    if "issuer" not in raptor.columns or "currency" not in raptor.columns:
        return action_1(raptor)
    g = raptor.groupby(["issuer", "currency"], observed=True)
    if "spread_bps" in raptor.columns:
        out = g["spread_bps"].agg(count="count", mean="mean", p95=lambda s: float(np.nanpercentile(pd.to_numeric(s, errors="coerce"), 95)))
    else:
        out = g.size().to_frame("count")
    return out.reset_index()


def action_5(raptor: pd.DataFrame) -> pd.DataFrame:
    _require_df(raptor, "Raptor")
    if "maturity" not in raptor.columns:
        return action_1(raptor)
    m = pd.to_datetime(raptor["maturity"], errors="coerce")
    days = (m - pd.Timestamp.now()).dt.days
    buckets = pd.cut(days, bins=[-10_000, 0, 7, 30, 90, 180, 365, 10_000], labels=["expired", "0-7d", "7-30d", "1-3m", "3-6m", "6-12m", "1y+"])
    df = raptor.copy()
    df["mat_bucket"] = buckets.astype("string")
    gcols = [c for c in ["issuer", "mat_bucket"] if c in df.columns] or ["mat_bucket"]
    use = [c for c in ["open_interest", "volume_1d", "spread_bps"] if c in df.columns] or df.select_dtypes(include="number").columns.tolist()[:3]
    out = df.groupby(gcols, observed=True)[use].agg(["count", "mean"])
    out.columns = ["_".join([a, b]) for a, b in out.columns.to_flat_index()]
    return out.reset_index()


def action_issuer_plot_table(raptor: pd.DataFrame) -> pd.DataFrame:
    _require_df(raptor, "Raptor")
    if "issuer" not in raptor.columns:
        return pd.DataFrame({"info": ["Missing issuer column"]})
    out = raptor.groupby("issuer", observed=True).agg(
        count=("issuer", "size"),
        avg_spread_bps=("spread_bps", "mean") if "spread_bps" in raptor.columns else ("issuer", "size"),
        avg_strike=("strike", "mean") if "strike" in raptor.columns else ("issuer", "size"),
    ).reset_index()
    return out


def action_7(raptor: pd.DataFrame) -> pd.DataFrame:
    _require_df(raptor, "Raptor")
    if "delta" not in raptor.columns:
        return action_2(raptor)
    out = raptor.assign(abs_delta=pd.to_numeric(raptor["delta"], errors="coerce").abs())
    out = out.sort_values("abs_delta", ascending=False, na_position="last").head(800)
    cols = [c for c in ["scheme_id", "issuer", "product", "callput", "underlying_isin", "strike", "Bid", "Ask", "delta", "abs_delta", "iv_30d"] if c in out.columns]
    if cols:
        out = out[cols]
    return out.reset_index(drop=True)
