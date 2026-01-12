from __future__ import annotations

import pandas as pd

from ..data.raptor_data import make_fake_raptor_from_underlyings

def load_raptor(underlyings: pd.DataFrame, n_rows: int = 1_000_000, seed: int = 123) -> pd.DataFrame:
    """Load/generate the Raptor dataframe based on Underlyings."""
    return make_fake_raptor_from_underlyings(underlyings, n_rows=n_rows, seed=seed)
