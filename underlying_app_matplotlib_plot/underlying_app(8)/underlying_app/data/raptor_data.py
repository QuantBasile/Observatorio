
from __future__ import annotations

import numpy as np
import pandas as pd


def make_fake_raptor_from_underlyings(underlyings: pd.DataFrame, n_rows: int = 1_000_000, seed: int = 123) -> pd.DataFrame:
    """
    Create a large "Raptor" (scheine) dataframe derived from underlyings.

    Design goals:
    - large rows x ~40 cols
    - memory-conscious: mostly numeric + categoricals
    - includes keys that can be merged back to underlyings (underlying_isin/underlying_wkn)
    - includes columns used by actions: Issuer/Type/OptionType/Bid/Ask
    """
    rng = np.random.default_rng(seed)

    if underlyings is None or underlyings.empty:
        raise ValueError("Underlyings dataframe is empty. Load underlyings first.")

    if "isin" not in underlyings.columns or "wkn" not in underlyings.columns:
        key_col = underlyings.columns[0]
        keys = underlyings[key_col].astype("string").fillna("").to_numpy()
        isin = keys
        wkn = keys
    else:
        isin = underlyings["isin"].astype("string").fillna("").to_numpy()
        wkn = underlyings["wkn"].astype("string").fillna("").to_numpy()

    u_n = len(underlyings)
    pick = rng.integers(0, u_n, size=n_rows)

    underlying_isin = isin[pick]
    underlying_wkn = wkn[pick]

    scheme_id = np.array([f"SC{seed:03d}{i:07d}" for i in range(n_rows)], dtype=object)

    start = np.datetime64("2024-01-01")
    maturity_days = rng.integers(7, 365 * 3, size=n_rows).astype("timedelta64[D]")
    maturity = start + maturity_days

    issuer = rng.choice(["BNP", "SG", "HSBC", "CITI", "UBS", "DB"], size=n_rows)
    currency = rng.choice(["EUR", "USD", "GBP"], size=n_rows)
    Type = rng.choice(["Producto1", "Producto2", "Producto3"], size=n_rows)
    OptionType = rng.choice(["Call", "Put"], size=n_rows)

    px_bid = np.round(rng.lognormal(0.0, 0.6, size=n_rows), 3)
    px_ask = np.round(px_bid + rng.uniform(0.001, 0.05, size=n_rows), 3)
    px_last = np.round((px_bid + px_ask) / 2.0 + rng.normal(0, 0.01, size=n_rows), 3)

    sized_gap_ask = np.round((px_ask - px_bid) * rng.uniform(50, 250, size=n_rows), 6)

    df = pd.DataFrame({
        "scheme_id": scheme_id,
        "underlying_isin": underlying_isin,
        "underlying_wkn": underlying_wkn,

        "Issuer": issuer,
        "currency": currency,
        "Type": Type,
        "OptionType": OptionType,

        "Maturity": pd.to_datetime(maturity),

        # NOTE: keep exact column casing expected by the UI/actions
        "Strike": np.round(rng.lognormal(3.4, 0.35, size=n_rows), 2),
        "leverage": np.round(rng.uniform(1.0, 25.0, size=n_rows), 2),
        "barrier": np.round(rng.lognormal(3.35, 0.40, size=n_rows), 2),
        "open_interest": rng.integers(0, 200000, size=n_rows),
        "volume_1d": rng.integers(0, 50000, size=n_rows),
        "spread_bps": np.round(rng.uniform(5, 250, size=n_rows), 1),
        "iv_30d": np.round(rng.uniform(0.10, 1.20, size=n_rows), 4),

        "delta": np.round(rng.uniform(-1, 1, size=n_rows), 4),
        "gamma": np.round(rng.uniform(0, 0.5, size=n_rows), 5),
        "vega": np.round(rng.uniform(0, 2.0, size=n_rows), 5),
        "theta": np.round(rng.uniform(-2.0, 0.0, size=n_rows), 5),
        "rho": np.round(rng.uniform(-1.0, 1.0, size=n_rows), 5),

        "px_bid": px_bid,
        "px_ask": px_ask,
        "px_last": px_last,

        "Bid": px_bid,
        "Ask": px_ask,

        "Sized_GAP_Ask": sized_gap_ask,

        "is_listed": rng.choice([True, False], size=n_rows, p=[0.97, 0.03]),
        "risk_bucket": rng.integers(1, 6, size=n_rows),
        "updated_at": pd.Timestamp.now().floor("s"),
    })

    target_cols = 40
    for k in range(1, max(1, target_cols - df.shape[1] + 1)):
        df[f"metric_{k:02d}"] = np.round(rng.normal(0.0, 1.0, size=n_rows), 4)

    for c in ["scheme_id", "underlying_isin", "underlying_wkn", "Issuer", "currency", "Type", "OptionType"]:
        if c in df.columns:
            df[c] = df[c].astype("category")

    return df
