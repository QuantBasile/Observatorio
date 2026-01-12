from __future__ import annotations

import pandas as pd


def _require_df(df: pd.DataFrame | None, name: str):
    if df is None or df.empty:
        raise ValueError(f"{name} dataframe is empty. Load it first.")


def table(raptor: pd.DataFrame) -> pd.DataFrame:
    """Backing table for the 'Issuer Plot' view (no aggregation).

    Returns *raw points* so each row corresponds to a single point that can be highlighted.
    Required columns:
      - Strike (x)
      - Sized_GAP_Ask (y)
      - Issuer, Type, Maturity, underlying_isin (for filtering)
      - Bid, Ask
    """
    _require_df(raptor, "Raptor")

    # Canonical columns (support legacy fallbacks)
    col_issuer = "Issuer" if "Issuer" in raptor.columns else ("issuer" if "issuer" in raptor.columns else ("ISSUER" if "ISSUER" in raptor.columns else None))
    col_type   = "Type" if "Type" in raptor.columns else ("product" if "product" in raptor.columns else None)
    col_opt    = "OptionType" if "OptionType" in raptor.columns else ("callput" if "callput" in raptor.columns else ("type" if "type" in raptor.columns else None))
    col_mat    = "Maturity" if "Maturity" in raptor.columns else ("maturity" if "maturity" in raptor.columns else None)

    # User's Raptor uses underlying_isin
    col_under  = "underlying_isin" if "underlying_isin" in raptor.columns else None

    col_strike = "Strike" if "Strike" in raptor.columns else ("strike" if "strike" in raptor.columns else None)
    col_gap    = "Sized_GAP_Ask" if "Sized_GAP_Ask" in raptor.columns else None
    col_bid    = "Bid" if "Bid" in raptor.columns else ("bid" if "bid" in raptor.columns else None)
    col_ask    = "Ask" if "Ask" in raptor.columns else ("ask" if "ask" in raptor.columns else None)

    required = [
        ("Issuer", col_issuer),
        ("Type", col_type),
        ("Maturity", col_mat),
        ("underlying_isin", col_under),
        ("Strike", col_strike),
        ("Sized_GAP_Ask", col_gap),
        ("Bid", col_bid),
        ("Ask", col_ask),
    ]
    missing = [n for n, c in required if c is None]
    if missing:
        return pd.DataFrame({"info": [f"Missing required columns: {', '.join(missing)}"]})

    base_cols = {
        "Issuer": col_issuer,
        "Type": col_type,
        "OptionType": col_opt,
        "Maturity": col_mat,
        "underlying_isin": col_under,
        "Strike": col_strike,
        "Sized_GAP_Ask": col_gap,
        "Bid": col_bid,
        "Ask": col_ask,
    }

    # Keep a few extra columns if present (but DO NOT duplicate base columns)
    extra_keep_candidates = ["spot", "Spot", "delta", "gamma", "vega", "theta", "rho", "spread_bps"]
    extra_keep = [c for c in extra_keep_candidates if c in raptor.columns]

    cols_in = list(dict.fromkeys([c for c in base_cols.values() if c is not None] + extra_keep))

    out = raptor.loc[:, cols_in].copy()

    # Rename to canonical names
    rename_map = {v: k for k, v in base_cols.items() if v is not None}
    out = out.rename(columns=rename_map)

    # Coerce numerics
    for c in ["Strike", "Sized_GAP_Ask", "Bid", "Ask"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    out = out.dropna(subset=["Strike", "Sized_GAP_Ask"])
    out = out.sort_values(by=["Sized_GAP_Ask", "Strike"], ascending=[False, True], kind="mergesort")

    # Column order (nice for the table)
    preferred = ["Issuer", "Type", "OptionType", "Maturity", "underlying_isin", "Strike", "Sized_GAP_Ask", "Bid", "Ask"]
    rest = [c for c in out.columns if c not in preferred]
    out = out.loc[:, preferred + rest]

    return out
