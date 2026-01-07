
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import pandas as pd

from ..data.model import DataModel
from .data_table import DataTable


class UnderlyingsView(ttk.Frame):
    """
    Center view: compact global search + per-column simple filters + table.

    Responsive behavior:
    - Filter "tiles" wrap based on available width (rebuilds when window is resized).
    - Table expands/shrinks with the window; columns keep fitted widths and horizontal scroll shows overflow.

    Filtering:
    - Numeric columns: no filter widget
    - Non-numeric: Combobox (typeable) with suggestions; applied as "contains" (case-insensitive)

    Shows dtype per column next to the filter label.
    """
    SUGGESTIONS_MAX = 50
    TILE_W_PX = 240   # approximate tile width used to compute wrap columns
    MIN_WRAP = 2
    MAX_WRAP = 8

    def __init__(self, parent: tk.Misc, model: DataModel, on_log):
        super().__init__(parent, style="Panel.TFrame")
        self.model = model
        self.on_log = on_log

        self._df: pd.DataFrame | None = None
        self._wrap_per_row = 6

        self._uniques_cache: dict[str, list[str]] = {}
        self._filter_vars: dict[str, tk.StringVar] = {}
        self._filter_widgets: dict[str, ttk.Combobox] = {}

        header = ttk.Frame(self, style="Panel.TFrame")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        header.columnconfigure(0, weight=1)

        self.title_lbl = ttk.Label(header, text="Underlyings", style="Title.TLabel")
        self.title_lbl.grid(row=0, column=0, sticky="w")

        self.count_lbl = ttk.Label(header, text="", style="Muted.TLabel")
        self.count_lbl.grid(row=0, column=1, sticky="e")

        self.filters_frame = ttk.Frame(self, style="Panel.TFrame")
        self.filters_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))

        # rebuild filters when the available width changes (maximize/minimize)
        self.filters_frame.bind("<Configure>", self._on_filters_resize)

        self.table = DataTable(self)
        self.table.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))

        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)

    def set_dataframe(self, df: pd.DataFrame):
        self._df = df
        self.model.set_df(df)
        self._build_filter_area(df)
        self._refresh()

    def _dtype_tag(self, s: pd.Series) -> str:
        if pd.api.types.is_datetime64_any_dtype(s):
            return "datetime"
        if pd.api.types.is_bool_dtype(s):
            return "bool"
        if pd.api.types.is_integer_dtype(s):
            return "int"
        if pd.api.types.is_float_dtype(s):
            return "float"
        if pd.api.types.is_categorical_dtype(s):
            return "category"
        return "str"

    def _compute_wrap(self, width_px: int) -> int:
        if width_px <= 1:
            return self._wrap_per_row
        n = max(self.MIN_WRAP, min(self.MAX_WRAP, width_px // self.TILE_W_PX))
        return int(n)

    def _on_filters_resize(self, evt):
        if self._df is None:
            return
        new_wrap = self._compute_wrap(evt.width)
        if new_wrap != self._wrap_per_row:
            self._wrap_per_row = new_wrap
            # rebuild with the new wrap
            self._build_filter_area(self._df)

    def _build_filter_area(self, df: pd.DataFrame):
        for w in self.filters_frame.winfo_children():
            w.destroy()

        self._uniques_cache.clear()
        self._filter_vars.clear()
        self._filter_widgets.clear()

        r = 0
        c = 0
        WRAP = self._wrap_per_row

        # Global search tile
        search_box = ttk.Frame(self.filters_frame, style="Panel.TFrame")
        search_box.grid(row=r, column=c, padx=6, pady=6, sticky="w")

        ttk.Label(search_box, text="Search", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(search_box, text="(global)", style="Muted.TLabel").grid(row=0, column=1, sticky="w", padx=(6, 0))

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_box, textvariable=self.search_var, width=18)
        self.search_entry.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))
        self.search_entry.bind("<KeyRelease>", self._on_global_search)

        c += 1
        if c >= WRAP:
            c = 0
            r += 1

        # Clear button tile
        clear_box = ttk.Frame(self.filters_frame, style="Panel.TFrame")
        clear_box.grid(row=r, column=c, padx=6, pady=6, sticky="w")
        ttk.Label(clear_box, text=" ", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        self.clear_btn = ttk.Button(clear_box, text="Clear", style="Accent.TButton", command=self._clear_filters)
        self.clear_btn.grid(row=1, column=0, sticky="w", pady=(2, 0))

        c += 1
        if c >= WRAP:
            c = 0
            r += 1

        # Column filters
        for col in df.columns:
            s = df[col]
            if pd.api.types.is_numeric_dtype(s):
                continue

            box = ttk.Frame(self.filters_frame, style="Panel.TFrame")
            box.grid(row=r, column=c, padx=6, pady=6, sticky="w")

            dtype = self._dtype_tag(s)
            ttk.Label(box, text=str(col), style="Muted.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(box, text=f"[{dtype}]", style="Muted.TLabel").grid(row=0, column=1, sticky="w", padx=(6, 0))

            var = tk.StringVar(value="All")
            cb = ttk.Combobox(box, textvariable=var, state="normal", width=18)

            uniques = self._compute_uniques(s)
            self._uniques_cache[col] = uniques
            cb["values"] = ["All"] + uniques[:self.SUGGESTIONS_MAX]
            cb.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))

            cb.bind("<<ComboboxSelected>>", lambda e, cc=col, vv=var: self._on_col_filter(cc, vv.get()))
            cb.bind("<KeyRelease>", lambda e, cc=col, vv=var, w=cb: self._on_col_typed(cc, vv, w))

            self._filter_vars[col] = var
            self._filter_widgets[col] = cb

            c += 1
            if c >= WRAP:
                c = 0
                r += 1

    def _compute_uniques(self, s: pd.Series) -> list[str]:
        # Robust unique extraction: treat NaN/None/empty as empty and exclude them from suggestions
        if pd.api.types.is_datetime64_any_dtype(s):
            s2 = pd.to_datetime(s, errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")
        else:
            s2 = s.astype("string").fillna("")
        vals = pd.unique(s2)
        vals = [v for v in vals if v not in ("", "<NA>", "nan", "NaN")]
        return sorted(vals)

    def _on_col_typed(self, col: str, var: tk.StringVar, widget: ttk.Combobox):
        txt = (var.get() or "").strip()
        base = self._uniques_cache.get(col, [])

        if not txt or txt == "All":
            widget["values"] = ["All"] + base[:self.SUGGESTIONS_MAX]
            self.model.set_col_filter(col, "All")
            self._refresh()
            return

        q = txt.lower()
        matches = [v for v in base if q in v.lower()]
        widget["values"] = ["All"] + matches[:self.SUGGESTIONS_MAX]

        self.model.set_col_filter(col, txt)
        self._refresh()

    def _on_col_filter(self, col: str, selected: str):
        self.model.set_col_filter(col, selected)
        self._refresh()
        self.on_log(f"Filter: {col} contains '{selected}'" if selected != "All" else f"Filter cleared: {col}")

    def _on_global_search(self, _evt=None):
        self.model.set_global_search(self.search_var.get())
        self._refresh()

    def _clear_filters(self):
        self.model.clear_filters()
        if hasattr(self, "search_var"):
            self.search_var.set("")
        for col, var in self._filter_vars.items():
            var.set("All")
        for col, cb in self._filter_widgets.items():
            base = self._uniques_cache.get(col, [])
            cb["values"] = ["All"] + base[:self.SUGGESTIONS_MAX]
        self._refresh()
        self.on_log("All filters cleared")

    def _refresh(self):
        if self.model.view is None:
            self.table.clear()
            self.count_lbl.configure(text="")
            return
        dfv = self.model.view
        self.count_lbl.configure(text=f"{len(dfv):,} rows × {dfv.shape[1]} cols")
        self.table.set_dataframe(dfv)
