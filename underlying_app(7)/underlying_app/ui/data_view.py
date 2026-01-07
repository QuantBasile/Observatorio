
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import pandas as pd

from ..data.model import DataModel
from .data_table import DataTable


class DataView(ttk.Frame):
    """
    Generic view:
      - Optional filters panel (enable_filters)
      - Table with sorting + autofit
      - Optional row_limit: show first N rows but keep total count visible
      - Quick stats bar (lightweight, general)

    For huge frames:
      - debounced filtering to reduce lag
      - suggestions capped
    """
    SUGGESTIONS_MAX = 50
    TILE_W_PX = 240
    MIN_WRAP = 2
    MAX_WRAP = 8
    DEBOUNCE_MS = 250

    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        model: DataModel,
        on_log,
        row_limit: int | None = None,
        enable_filters: bool = True,
        show_stats: bool = True,
        stats_sample_rows: int = 2000,
    ):
        super().__init__(parent, style="Panel.TFrame")
        self.model = model
        self.on_log = on_log
        self.title = title
        self.row_limit = row_limit
        self.enable_filters = enable_filters
        self.show_stats = show_stats
        self.stats_sample_rows = stats_sample_rows

        self._df: pd.DataFrame | None = None
        self._wrap_per_row = 6
        self._pending_job: str | None = None

        self._uniques_cache: dict[str, list[str]] = {}
        self._filter_vars: dict[str, tk.StringVar] = {}
        self._filter_widgets: dict[str, ttk.Combobox] = {}

        # --- Header row ---
        header = ttk.Frame(self, style="Panel.TFrame")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        header.columnconfigure(0, weight=1)

        self.title_lbl = ttk.Label(header, text=self.title, style="Title.TLabel")
        self.title_lbl.grid(row=0, column=0, sticky="w")

        self.count_lbl = ttk.Label(header, text="", style="Muted.TLabel")
        self.count_lbl.grid(row=0, column=1, sticky="e")

        # --- Quick stats row ---
        if self.show_stats:
            self.stats_frame = ttk.Frame(self, style="Panel.TFrame")
            self.stats_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
            for i in range(5):
                self.stats_frame.columnconfigure(i, weight=0)
            self._stat_labels = [ttk.Label(self.stats_frame, text="", style="Muted.TLabel") for _ in range(5)]
            for i, lbl in enumerate(self._stat_labels):
                lbl.grid(row=0, column=i, sticky="w", padx=(0 if i == 0 else 18, 0))
            next_row = 2
        else:
            self.stats_frame = None
            self._stat_labels = []
            next_row = 1

        # --- Filters row (optional) ---
        if self.enable_filters:
            self.filters_frame = ttk.Frame(self, style="Panel.TFrame")
            self.filters_frame.grid(row=next_row, column=0, sticky="ew", padx=12, pady=(0, 8))
            self.filters_frame.bind("<Configure>", self._on_filters_resize)
            table_row = next_row + 1
        else:
            self.filters_frame = None
            table_row = next_row

        # --- Table ---
        self.table = DataTable(self)
        self.table.grid(row=table_row, column=0, sticky="nsew", padx=12, pady=(0, 12))

        self.rowconfigure(table_row, weight=1)
        self.columnconfigure(0, weight=1)

    def set_dataframe(self, df: pd.DataFrame):
        self._df = df
        self.model.set_df(df)
        if self.enable_filters:
            self._build_filter_area(df)
        self._refresh()

    # ---------------- Dtypes & layout ----------------
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
        if self._df is None or self.filters_frame is None:
            return
        new_wrap = self._compute_wrap(evt.width)
        if new_wrap != self._wrap_per_row:
            self._wrap_per_row = new_wrap
            self._build_filter_area(self._df)

    # ---------------- Filters UI ----------------
    def _build_filter_area(self, df: pd.DataFrame):
        if self.filters_frame is None:
            return
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
        self.search_entry.bind("<KeyRelease>", self._debounced_apply)

        c += 1
        if c >= WRAP:
            c = 0
            r += 1

        # Clear tile
        clear_box = ttk.Frame(self.filters_frame, style="Panel.TFrame")
        clear_box.grid(row=r, column=c, padx=6, pady=6, sticky="w")
        ttk.Label(clear_box, text=" ", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        self.clear_btn = ttk.Button(clear_box, text="Clear", style="Accent.TButton", command=self._clear_filters)
        self.clear_btn.grid(row=1, column=0, sticky="w", pady=(2, 0))

        c += 1
        if c >= WRAP:
            c = 0
            r += 1

        # Column filters (non-numeric only)
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

            cb.bind("<<ComboboxSelected>>", lambda e, cc=col, vv=var: self._on_col_selected(cc, vv.get()))
            cb.bind("<KeyRelease>", lambda e, cc=col, vv=var, w=cb: self._on_col_typed(cc, vv, w))

            self._filter_vars[col] = var
            self._filter_widgets[col] = cb

            c += 1
            if c >= WRAP:
                c = 0
                r += 1

    def _compute_uniques(self, s: pd.Series) -> list[str]:
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
        else:
            q = txt.lower()
            matches = [v for v in base if q in v.lower()]
            widget["values"] = ["All"] + matches[:self.SUGGESTIONS_MAX]

        self._debounced_apply()

    def _on_col_selected(self, col: str, selected: str):
        self.model.set_col_filter(col, selected)
        self._refresh()
        self.on_log(f"Filter: {col} contains '{selected}'" if selected != "All" else f"Filter cleared: {col}")

    def _debounced_apply(self, _evt=None):
        if self._pending_job is not None:
            try:
                self.after_cancel(self._pending_job)
            except Exception:
                pass
        self._pending_job = self.after(self.DEBOUNCE_MS, self._apply_filters_now)

    def _apply_filters_now(self):
        self._pending_job = None
        for col, var in self._filter_vars.items():
            self.model.set_col_filter(col, var.get())
        self.model.set_global_search(getattr(self, "search_var", tk.StringVar()).get())
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

    # ---------------- Stats ----------------
    def _set_stats(self, df: pd.DataFrame, shown_rows: int, total_rows: int):
        if not self.show_stats or not self._stat_labels:
            return

        # keep stats lightweight: use up to stats_sample_rows from the shown df
        try:
            sample = df.head(min(self.stats_sample_rows, len(df)))
        except Exception:
            sample = df

        ncols = sample.shape[1]
        num_cols = int(sample.select_dtypes(include="number").shape[1])
        dt_cols = int(sample.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).shape[1])
        cat_cols = int(sample.select_dtypes(include=["category"]).shape[1])
        # non-null % on sample
        try:
            nonnull = float(sample.notna().mean().mean() * 100)
        except Exception:
            nonnull = 0.0

        self._stat_labels[0].configure(text=f"Cols: {ncols}")
        self._stat_labels[1].configure(text=f"Types: {num_cols} num · {dt_cols} dt · {cat_cols} cat")
        self._stat_labels[2].configure(text=f"Completeness: {nonnull:0.1f}%")
        # show displayed/total if different
        if total_rows != shown_rows:
            self._stat_labels[3].configure(text=f"Displayed: {shown_rows:,} / {total_rows:,}")
        else:
            self._stat_labels[3].configure(text=f"Rows: {total_rows:,}")
        # tiny “hint”
        self._stat_labels[4].configure(text="Tip: click headers to sort ▲▼")

    # ---------------- Refresh ----------------
    def _refresh(self):
        if self.model.view is None:
            self.table.clear()
            self.count_lbl.configure(text="")
            if self.show_stats and self._stat_labels:
                for lbl in self._stat_labels:
                    lbl.configure(text="")
            return

        dfv = self.model.view
        total = len(dfv)

        if self.row_limit is not None and total > self.row_limit:
            shown = self.row_limit
            shown_df = dfv.head(self.row_limit)
            self.count_lbl.configure(text=f"total {total:,} rows | showing {shown:,}")
        else:
            shown_df = dfv
            shown = total
            self.count_lbl.configure(text=f"{total:,} rows × {dfv.shape[1]} cols")

        self._set_stats(shown_df, shown_rows=shown, total_rows=total)
        self.table.set_dataframe(shown_df)
