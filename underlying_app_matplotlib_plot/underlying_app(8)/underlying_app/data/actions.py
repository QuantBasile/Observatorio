
from __future__ import annotations

import numpy as np
import pandas as pd


def _require_df(df: pd.DataFrame | None, name: str):
    if df is None or df.empty:
        raise ValueError(f"{name} dataframe is empty. Load it first.")


def action_1(raptor: pd.DataFrame) -> pd.DataFrame:
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


def action_2(raptor: pd.DataFrame) -> pd.DataFrame:
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
    if "Issuer" not in raptor.columns or "currency" not in raptor.columns:
        return action_1(raptor)
    g = raptor.groupby(["Issuer", "currency"], observed=True)
    if "spread_bps" in raptor.columns:
        out = g["spread_bps"].agg(count="count", mean="mean", p95=lambda s: float(np.nanpercentile(pd.to_numeric(s, errors="coerce"), 95)))
    else:
        out = g.size().to_frame("count")
    return out.reset_index()


def action_5(raptor: pd.DataFrame) -> pd.DataFrame:
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


def action_issuer_plot_table(raptor: pd.DataFrame) -> pd.DataFrame:
    """Table backing the 'Issuer Plot' view.

    This is intentionally **not** a groupby/aggregation: we return a filtered slice of the raw
    Raptor dataframe so a table row corresponds to a concrete point that can be highlighted
    in the plot.

    Required columns for plotting:
      - Strike (x)
      - Sized_GAP_Ask (y)
      - Issuer, Type, Maturity (for filtering / coloring)
      - Bid, Ask (requested)
    """
    _require_df(raptor, "Raptor")

    # Resolve canonical column names with safe fallbacks
    col_issuer = "Issuer" if "Issuer" in raptor.columns else ("issuer" if "issuer" in raptor.columns else ("ISSUER" if "ISSUER" in raptor.columns else None))
    col_type = "Type" if "Type" in raptor.columns else ("product" if "product" in raptor.columns else None)
    col_opt = "OptionType" if "OptionType" in raptor.columns else ("callput" if "callput" in raptor.columns else ("type" if "type" in raptor.columns else None))
    col_mat = "Maturity" if "Maturity" in raptor.columns else ("maturity" if "maturity" in raptor.columns else None)

    # Ensure mandatory plot cols exist (Strike, Sized_GAP_Ask, Bid, Ask)
    col_strike = "Strike" if "Strike" in raptor.columns else ("strike" if "strike" in raptor.columns else None)
    col_gap = "Sized_GAP_Ask" if "Sized_GAP_Ask" in raptor.columns else None
    col_bid = "Bid" if "Bid" in raptor.columns else ("bid" if "bid" in raptor.columns else None)
    col_ask = "Ask" if "Ask" in raptor.columns else ("ask" if "ask" in raptor.columns else None)

    missing = [n for n, c in [("Issuer", col_issuer), ("Type", col_type), ("Maturity", col_mat),
                             ("Strike", col_strike), ("Sized_GAP_Ask", col_gap), ("Bid", col_bid), ("Ask", col_ask)] if c is None]
    if missing:
        return pd.DataFrame({"info": [f"Missing required columns: {', '.join(missing)}"]})

    # Build output slice, keeping a few extra useful columns if present
    base_cols = {
        "Issuer": col_issuer,
        "Type": col_type,
        "OptionType": col_opt,
        "Maturity": col_mat,
        "Strike": col_strike,
        "Sized_GAP_Ask": col_gap,
        "Bid": col_bid,
        "Ask": col_ask,
    }
    extra_keep = [c for c in ["Underlying", "underlying", "spot", "Spot", "delta", "gamma", "vega", "theta", "rho", "spread_bps"] if c in raptor.columns]
    cols_in = [c for c in base_cols.values() if c is not None] + extra_keep

    out = raptor.loc[:, cols_in].copy()

    # Rename to canonical names
    rename_map = {v: k for k, v in base_cols.items() if v is not None}
    out = out.rename(columns=rename_map)

    # Coerce dtypes for better sorting/filtering
    out["Strike"] = pd.to_numeric(out["Strike"], errors="coerce")
    out["Sized_GAP_Ask"] = pd.to_numeric(out["Sized_GAP_Ask"], errors="coerce")
    out["Bid"] = pd.to_numeric(out["Bid"], errors="coerce")
    out["Ask"] = pd.to_numeric(out["Ask"], errors="coerce")

    # Sort: biggest gaps first, then strike
    out = out.sort_values(by=["Sized_GAP_Ask", "Strike"], ascending=[False, True], kind="mergesort")

    return out


def action_7(raptor: pd.DataFrame) -> pd.DataFrame:
    _require_df(raptor, "Raptor")
    if "delta" not in raptor.columns:
        return action_2(raptor)
    out = raptor.assign(abs_delta=pd.to_numeric(raptor["delta"], errors="coerce").abs())
    out = out.sort_values("abs_delta", ascending=False, na_position="last").head(800)
    cols = [c for c in ["scheme_id", "Issuer", "Type", "OptionType", "Bid", "Ask", "delta", "abs_delta", "iv_30d"] if c in out.columns]
    if cols:
        out = out[cols]
    return out.reset_index(drop=True)
