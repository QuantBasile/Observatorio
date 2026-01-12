from __future__ import annotations

import pandas as pd

from ..data.fake_data import make_fake_underlyings

def load_underlyings(n_rows: int = 700, seed: int = 42) -> pd.DataFrame:
    """Load/generate the Underlyings dataframe."""
    return make_fake_underlyings(n_rows=n_rows, seed=seed)
