
from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import tkinter as tk
from tkinter import ttk


class DataTable(ttk.Frame):
    BIG_DF_ROW_THRESHOLD = 20000
    SAMPLE_FOR_WIDTH = 5000
    CHAR_PX = 7
    PADDING_PX = 24
    MIN_PX = 80
    MAX_PX = 1200

    def __init__(self, parent: tk.Misc, on_copy=None):
        super().__init__(parent, style="Panel.TFrame")
        self.on_copy = on_copy

        self.tree = ttk.Treeview(self, columns=(), show="headings", selectmode="extended")
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
        self._last_cell_value: str | None = None

        self.tree.bind("<Button-1>", self._on_single_click, add=True)
        self.tree.bind("<Double-1>", self._on_double_click, add=True)
        self.tree.bind("<Control-c>", self._on_ctrl_c, add=True)
        self.tree.bind("<Control-C>", self._on_ctrl_c, add=True)

    def set_dataframe(self, df: pd.DataFrame):
        self._df = df.copy()
        self._sort_col = None
        self._sort_asc = True
        self._last_cell_value = None
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
        self._last_cell_value = None

    def _col_anchor_for_dtype(self, s: pd.Series) -> str:
        if pd.api.types.is_numeric_dtype(s):
            return "e"
        if pd.api.types.is_datetime64_any_dtype(s):
            return "center"
        return "w"

    def _format_value(self, v):
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
        df = self._df
        if df is None or df.empty:
            return

        if len(df) > self.BIG_DF_ROW_THRESHOLD:
            sample = df.sample(n=min(self.SAMPLE_FOR_WIDTH, len(df)), random_state=0)
        else:
            sample = df

        for c in df.columns:
            header_len = len(self._heading_text(c))
            max_len = header_len
            try:
                if pd.api.types.is_datetime64_any_dtype(sample[c]):
                    s_str = pd.to_datetime(sample[c], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")
                else:
                    s_str = sample[c].astype("string").fillna("")
                m = s_str.map(len).max()
                if pd.notna(m):
                    max_len = max(max_len, int(m))
            except Exception:
                pass

            px = int(max_len * self.CHAR_PX + self.PADDING_PX)
            px = max(self.MIN_PX, min(self.MAX_PX, px))
            anchor = self._col_anchor_for_dtype(df[c])
            self.tree.column(c, width=px, anchor=anchor, stretch=False)

    # --- Copy support ---
    def _cell_at_event(self, event):
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or not col_id:
            return None
        try:
            col_index = int(col_id.replace("#", "")) - 1
        except Exception:
            return None
        cols = list(self.tree["columns"])
        if col_index < 0 or col_index >= len(cols):
            return None
        values = self.tree.item(row_id, "values")
        if not values:
            return None
        try:
            val = values[col_index]
        except Exception:
            val = ""
        return str(val)

    def _copy_to_clipboard(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        self._last_cell_value = text
        if self.on_copy:
            try:
                self.on_copy(text)
            except Exception:
                pass

    def _on_single_click(self, event):
        cell = self._cell_at_event(event)
        if cell is not None:
            self._last_cell_value = cell

    def _on_double_click(self, event):
        cell = self._cell_at_event(event)
        if cell is not None:
            self._copy_to_clipboard(cell)

    def _on_ctrl_c(self, event=None):
        if self._last_cell_value is not None:
            self._copy_to_clipboard(self._last_cell_value)
            return "break"

        sel = self.tree.selection()
        if not sel:
            return "break"
        lines = []
        for item in sel:
            vals = self.tree.item(item, "values")
            lines.append("\t".join(str(v) for v in vals))
        self._copy_to_clipboard("\n".join(lines))
        return "break"
