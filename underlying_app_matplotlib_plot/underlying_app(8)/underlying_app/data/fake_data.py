
from __future__ import annotations

from datetime import date
import random
import string

import numpy as np
import pandas as pd


def _rand_isin(rng: np.random.Generator) -> str:
    # Fake ISIN: 2 letters + 10 alnum
    cc = rng.choice(["DE", "FR", "ES", "NL", "IT", "US", "GB"])
    body = "".join(rng.choice(list(string.ascii_uppercase + string.digits), size=10))
    return f"{cc}{body}"


def _rand_wkn(rng: np.random.Generator) -> str:
    # Fake WKN: 6 chars
    body = "".join(rng.choice(list(string.ascii_uppercase + string.digits), size=6))
    return body


def make_fake_underlyings(n_rows: int = 700, seed: int = 42) -> pd.DataFrame:
    """
    Generates a "realistic enough" underlyings dataframe.

    Required columns:
      - isin, wkn, name
      - EventNext (datetime64[ns])
      - EventChange (float, e.g. 0.03 for 3%)

    NOTE: careful to avoid immutable pandas Index operations.
    """
    rng = np.random.default_rng(seed)
    today = pd.Timestamp(date.today())

    sectors = np.array(["Tech", "Industrials", "Financials", "Healthcare", "Energy", "Consumer", "Utilities"])
    countries = np.array(["DE", "FR", "ES", "NL", "IT", "US", "GB"])
    currencies = np.array(["EUR", "USD", "GBP"])
    ratings = np.array(["AAA", "AA", "A", "BBB", "BB", "B"])

    # Create event_next as a mutable numpy array (not a DatetimeIndex)
    day_offsets = rng.integers(-20, 60, size=n_rows)
    hour_offsets = rng.integers(0, 24, size=n_rows)
    event_next = (today.to_datetime64() + day_offsets.astype("timedelta64[D]") + hour_offsets.astype("timedelta64[h]")).astype("datetime64[ns]")

    # Force ~4% to "today"
    mask_today = rng.random(n_rows) < 0.04
    if mask_today.any():
        event_next[mask_today] = (today.to_datetime64() + rng.integers(6, 18, size=mask_today.sum()).astype("timedelta64[h]")).astype("datetime64[ns]")

    df = pd.DataFrame({
        "isin": [_rand_isin(rng) for _ in range(n_rows)],
        "wkn":  [_rand_wkn(rng) for _ in range(n_rows)],
        "name": [f"Company {i:04d}" for i in range(1, n_rows + 1)],

        "sector": rng.choice(sectors, size=n_rows),
        "country": rng.choice(countries, size=n_rows),
        "currency": rng.choice(currencies, size=n_rows),

        "px_last": np.round(rng.lognormal(mean=3.6, sigma=0.35, size=n_rows), 2),
        "mkt_cap_bn": np.round(rng.lognormal(mean=2.0, sigma=0.7, size=n_rows), 2),
        "vol_20d": np.round(rng.uniform(0.10, 0.80, size=n_rows), 4),
        "beta_1y": np.round(rng.normal(1.0, 0.35, size=n_rows), 3),
        "pe_fwd": np.round(rng.uniform(5, 35, size=n_rows), 2),
        "div_yield": np.round(rng.uniform(0.0, 0.08, size=n_rows), 4),
        "rating": rng.choice(ratings, size=n_rows),

        "EventNext": pd.to_datetime(event_next),
        "EventChange": np.round(rng.uniform(0.01, 0.12, size=n_rows), 4),  # 0.03 => 3%

        "updated_at": pd.Timestamp.now().floor("s"),
        "note": rng.choice(np.array(["", "Watch", "Earnings", "Dividend", "Split"]), size=n_rows,
                           p=np.array([0.75, 0.10, 0.08, 0.05, 0.02])),
    })

    # Ensure exactly 20 columns: add filler columns that still make sense
    # (keep them optional for your real DF later)
    df["spread_bps"] = np.round(rng.uniform(5, 200, size=n_rows), 1)
    df["adv_usd_mn"] = np.round(rng.lognormal(mean=2.2, sigma=0.8, size=n_rows), 2)
    df["locate_ok"] = rng.choice([True, False], size=n_rows, p=[0.92, 0.08])
    df["risk_bucket"] = rng.integers(1, 6, size=n_rows)

    # Now we should have 20 columns
    return df
