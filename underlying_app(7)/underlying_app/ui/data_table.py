
from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import tkinter as tk
from tkinter import ttk


class DataTable(ttk.Frame):
    """
    Generic Treeview table for any pandas DataFrame.

    Features:
    - Column alignment by dtype:
        * numeric -> right
        * datetime -> center
        * other -> left
    - Sorting: click header toggles asc/desc.
      Shows arrow indicators in the header: ▲ (asc) / ▼ (desc)
    - Auto-fit column widths to show full content (may require horizontal scroll)
      * Uses full column for typical sizes, and safe sampling for very large frames.
    - Highlights rows where EventNext's DATE == today (if column exists)
    """
    BIG_DF_ROW_THRESHOLD = 20000     # beyond this, we sample for width to keep UI responsive
    SAMPLE_FOR_WIDTH = 5000          # sample size if very large
    CHAR_PX = 7                      # rough px per character for Segoe UI 10
    PADDING_PX = 24                  # extra padding per column
    MIN_PX = 80
    MAX_PX = 1200                    # allow very wide columns if needed, but keep somewhat sane

    def __init__(self, parent: tk.Misc):
        super().__init__(parent, style="Panel.TFrame")

        self.tree = ttk.Treeview(self, columns=(), show="headings")
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tree.tag_configure("event_today", background="#fff7d6")

        self._df: pd.DataFrame | None = None
        self._sort_col: str | None = None
        self._sort_asc: bool = True

    def set_dataframe(self, df: pd.DataFrame):
        self._df = df.copy()
        self._sort_col = None
        self._sort_asc = True
        self._rebuild_columns(self._df)
        self._populate_rows(self._df)
        self.autofit_columns()

    def clear(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree["columns"] = ()
        self._df = None
        self._sort_col = None
        self._sort_asc = True

    def _col_anchor_for_dtype(self, s: pd.Series) -> str:
        if pd.api.types.is_numeric_dtype(s):
            return "e"
        if pd.api.types.is_datetime64_any_dtype(s):
            return "center"
        return "w"

    def _format_value(self, v):
        # Robust formatting for NaN/None/empty strings/0/etc
        if v is None:
            return ""
        try:
            if pd.isna(v):
                return ""
        except Exception:
            pass
        if isinstance(v, (pd.Timestamp, datetime)):
            try:
                return pd.to_datetime(v).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                return str(v)
        return str(v)

    def _heading_text(self, col: str) -> str:
        if self._sort_col != col:
            return col
        return f"{col} {'▲' if self._sort_asc else '▼'}"

    def _rebuild_columns(self, df: pd.DataFrame):
        cols = list(df.columns)
        self.tree["columns"] = cols

        for c in cols:
            self.tree.heading(c, text=self._heading_text(c), command=lambda col=c: self._on_heading_click(col))
            anchor = self._col_anchor_for_dtype(df[c])
            # stretch=False => keep fitted width; horizontal scroll shows the rest
            self.tree.column(c, width=120, anchor=anchor, stretch=False)

    def _update_all_headings(self):
        if self._df is None:
            return
        for c in self._df.columns:
            self.tree.heading(c, text=self._heading_text(c))

    def _on_heading_click(self, col: str):
        if self._df is None or col not in self._df.columns:
            return

        if self._sort_col == col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col
            self._sort_asc = True

        s = self._df[col]
        asc = self._sort_asc

        try:
            if pd.api.types.is_datetime64_any_dtype(s):
                key = pd.to_datetime(s, errors="coerce")
            elif pd.api.types.is_numeric_dtype(s):
                key = pd.to_numeric(s, errors="coerce")
            else:
                key = s.astype("string").fillna("").str.lower()

            order = key.sort_values(ascending=asc, na_position="last").index
            self._df = self._df.loc[order]
        except Exception:
            self._df = self._df.sort_values(by=col, ascending=asc, kind="mergesort")

        self._update_all_headings()
        self._populate_rows(self._df)
        self.autofit_columns()

    def _populate_rows(self, df: pd.DataFrame):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if df is None or df.empty:
            return

        today = date.today()
        has_eventnext = "EventNext" in df.columns

        for _, row in df.iterrows():
            values = [self._format_value(row[c]) for c in df.columns]
            tags = ()

            if has_eventnext:
                try:
                    ev = pd.to_datetime(row["EventNext"], errors="coerce")
                    if pd.notna(ev) and ev.date() == today:
                        tags = ("event_today",)
                except Exception:
                    pass

            self.tree.insert("", "end", values=values, tags=tags)

    def autofit_columns(self):
        """
        Fit columns to show full content (header + cell values).
        Uses all rows for typical dataframes; for very large ones uses sampling.
        """
        df = self._df
        if df is None or df.empty:
            return

        # Choose data for width computation
        if len(df) > self.BIG_DF_ROW_THRESHOLD:
            sample = df.sample(n=min(self.SAMPLE_FOR_WIDTH, len(df)), random_state=0)
        else:
            sample = df  # full

        for c in df.columns:
            header_len = len(self._heading_text(c))
            max_len = header_len

            try:
                # Use vectorized conversion for speed & robustness
                if pd.api.types.is_datetime64_any_dtype(sample[c]):
                    s_str = pd.to_datetime(sample[c], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
                    s_str = s_str.fillna("")
                else:
                    # string dtype handles NaN -> <NA> so we fill to ""
                    s_str = sample[c].astype("string").fillna("")

                # include empty/0 properly; lengths compute ok
                m = s_str.map(len).max()
                if pd.notna(m):
                    max_len = max(max_len, int(m))
            except Exception:
                pass

            px = int(max_len * self.CHAR_PX + self.PADDING_PX)
            px = max(self.MIN_PX, min(self.MAX_PX, px))

            # keep current anchor
            anchor = self._col_anchor_for_dtype(df[c])
            self.tree.column(c, width=px, anchor=anchor, stretch=False)
