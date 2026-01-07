
from __future__ import annotations

import pandas as pd


class DataModel:
    """
    General-purpose model:
      - df: original dataframe
      - view: filtered dataframe
      - col_filters: per-column text filters (string/obj/cat/datetime only). Empty or "All" disables.
      - global_search: substring search across all non-numeric columns
    """
    def __init__(self):
        self.df: pd.DataFrame | None = None
        self.view: pd.DataFrame | None = None
        self.col_filters: dict[str, str] = {}
        self.global_search: str = ""

    def set_df(self, df: pd.DataFrame):
        self.df = df
        self.col_filters = {c: "All" for c in df.columns}
        self.global_search = ""
        self.apply_filters()

    def set_col_filter(self, column: str, text: str):
        if self.df is None or column not in self.df.columns:
            return
        self.col_filters[column] = text if text else "All"
        self.apply_filters()

    def set_global_search(self, text: str):
        self.global_search = (text or "").strip()
        self.apply_filters()

    def clear_filters(self):
        if self.df is None:
            return
        for c in self.df.columns:
            self.col_filters[c] = "All"
        self.global_search = ""
        self.apply_filters()

    def apply_filters(self):
        if self.df is None:
            self.view = None
            return

        df = self.df

        # Per-column filters (contains match, case-insensitive) for non-numeric columns only
        for col, filt in self.col_filters.items():
            if filt in ("", "All"):
                continue
            s = df[col]

            # No filters for numeric columns
            if pd.api.types.is_numeric_dtype(s):
                continue

            # datetime -> compare formatted string
            if pd.api.types.is_datetime64_any_dtype(s):
                s_str = pd.to_datetime(s, errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")
            else:
                s_str = s.astype("string").fillna("")

            needle = str(filt).lower()
            df = df[s_str.str.lower().str.contains(needle, na=False)]

        # Global search across all non-numeric columns
        q = self.global_search
        if q:
            ql = q.lower()
            mask = None
            for col in df.columns:
                s = df[col]
                if pd.api.types.is_numeric_dtype(s):
                    continue
                if pd.api.types.is_datetime64_any_dtype(s):
                    s_str = pd.to_datetime(s, errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")
                else:
                    s_str = s.astype("string").fillna("")
                m = s_str.str.lower().str.contains(ql, na=False)
                mask = m if mask is None else (mask | m)
            if mask is not None:
                df = df[mask]

        self.view = df
