
from __future__ import annotations

import numpy as np
import pandas as pd


def make_fake_raptor_from_underlyings(underlyings: pd.DataFrame, n_rows: int = 1_000_000, seed: int = 123) -> pd.DataFrame:
    """
    Create a large "Raptor" (scheine) dataframe derived from underlyings.

    Design goals:
    - 1M rows x ~40 cols
    - memory-conscious: mostly numeric + categoricals
    - includes keys that can be merged back to underlyings (isin/wkn or underlying_id)

    NOTE: In your real app, replace this with your real pipeline/merge logic.
    """
    rng = np.random.default_rng(seed)

    if underlyings is None or underlyings.empty:
        raise ValueError("Underlyings dataframe is empty. Load underlyings first.")

    # pick join keys from underlyings
    # keep as numpy arrays for speed
    if "isin" not in underlyings.columns or "wkn" not in underlyings.columns:
        # fall back to first column as an id
        key_col = underlyings.columns[0]
        keys = underlyings[key_col].astype("string").fillna("").to_numpy()
        isin = keys
        wkn = keys
    else:
        isin = underlyings["isin"].astype("string").fillna("").to_numpy()
        wkn = underlyings["wkn"].astype("string").fillna("").to_numpy()

    u_n = len(underlyings)
    pick = rng.integers(0, u_n, size=n_rows)

    # core identifiers
    underlying_isin = isin[pick]
    underlying_wkn = wkn[pick]

    # scheine identifiers (fake)
    # keep as strings but later convert to category for memory
    scheme_id = np.array([f"SC{seed:03d}{i:07d}" for i in range(n_rows)], dtype=object)

    # dates (as datetime64)
    start = np.datetime64("2024-01-01")
    maturity_days = rng.integers(7, 365*3, size=n_rows).astype("timedelta64[D]")
    maturity = start + maturity_days

    # mostly numeric columns
    df = pd.DataFrame({
        "scheme_id": scheme_id,
        "underlying_isin": underlying_isin,
        "underlying_wkn": underlying_wkn,
        "issuer": rng.choice(["BNP", "SG", "HSBC", "CITI", "UBS", "DB"], size=n_rows),
        "currency": rng.choice(["EUR", "USD", "GBP"], size=n_rows),
        "type": rng.choice(["Call", "Put", "Turbo", "KO", "Discount"], size=n_rows),
        "maturity": pd.to_datetime(maturity),

        "strike": np.round(rng.lognormal(3.4, 0.35, size=n_rows), 2),
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

        "px_bid": np.round(rng.lognormal(0.0, 0.6, size=n_rows), 3),
        "px_ask": np.round(rng.lognormal(0.0, 0.6, size=n_rows) + 0.02, 3),
        "px_last": np.round(rng.lognormal(0.0, 0.6, size=n_rows), 3),

        "is_listed": rng.choice([True, False], size=n_rows, p=[0.97, 0.03]),
        "risk_bucket": rng.integers(1, 6, size=n_rows),
        "updated_at": pd.Timestamp.now().floor("s"),
    })

    # Add filler numeric columns to reach ~40 columns
    for k in range(1, 41 - df.shape[1] + 1):
        df[f"metric_{k:02d}"] = np.round(rng.normal(0.0, 1.0, size=n_rows), 4)

    # Make some string columns categorical to reduce memory footprint
    for c in ["scheme_id", "underlying_isin", "underlying_wkn", "issuer", "currency", "type"]:
        if c in df.columns:
            df[c] = df[c].astype("category")

    return df
