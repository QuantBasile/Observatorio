
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import pandas as pd

from ..data.model import DataModel
from .data_table import DataTable
from .plot_canvas import PlotCanvas


class TablePlotView(ttk.Frame):
    def __init__(self, parent: tk.Misc, title: str, on_log, row_limit: int = 2000):
        super().__init__(parent, style="Panel.TFrame")
        self.on_log = on_log
        self.title = title
        self.row_limit = row_limit

        self.model = DataModel()

        header = ttk.Frame(self, style="Panel.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 6))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=title, style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.count_lbl = ttk.Label(header, text="", style="Muted.TLabel")
        self.count_lbl.grid(row=0, column=1, sticky="e")

        self.stats = ttk.Frame(self, style="Panel.TFrame")
        self.stats.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 8))
        self._stat_labels = [ttk.Label(self.stats, text="", style="Muted.TLabel") for _ in range(4)]
        for i, lbl in enumerate(self._stat_labels):
            lbl.grid(row=0, column=i, sticky="w", padx=(0 if i == 0 else 18, 0))

        self.body = ttk.Frame(self, style="Panel.TFrame")
        self.body.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=12, pady=(0, 12))
        # 50/50 split between table and plot (requested)
        # NOTE: ttk.Treeview requests a width roughly equal to the sum of all column widths.
        # If we don't force an even split, the table can "steal" almost all horizontal space
        # and leave the plot effectively invisible.
        self.body.columnconfigure(0, weight=1, uniform="split")
        self.body.columnconfigure(1, weight=1, uniform="split")
        self.body.rowconfigure(0, weight=1)

        self.table = DataTable(self.body, on_copy=lambda t: self.on_log(f"Copied: {t}"))
        self.table.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        # Give the plot a visible boundary so it's obvious it's there
        self.plot = PlotCanvas(self.body, background="#ffffff", bd=1, relief="solid")
        self.plot.grid(row=0, column=1, sticky="nsew")

        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)

        self.table.tree.bind("<<TreeviewSelect>>", self._on_select, add=True)

        self._plot_provider = None

    def set_plot_provider(self, fn):
        self._plot_provider = fn

    def set_dataframe(self, df: pd.DataFrame):
        self.model.set_df(df)
        self._refresh()

    def _set_stats(self, shown_df: pd.DataFrame, shown_rows: int, total_rows: int):
        ncols = shown_df.shape[1]
        num_cols = int(shown_df.select_dtypes(include="number").shape[1])
        dt_cols = int(shown_df.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).shape[1])
        cat_cols = int(shown_df.select_dtypes(include=["category"]).shape[1])

        self._stat_labels[0].configure(text=f"Cols: {ncols}")
        self._stat_labels[1].configure(text=f"Types: {num_cols} num · {dt_cols} dt · {cat_cols} cat")
        self._stat_labels[2].configure(text=f"Displayed: {shown_rows:,} / {total_rows:,}" if shown_rows != total_rows else f"Rows: {total_rows:,}")
        self._stat_labels[3].configure(text="Select a row → updates plot")

    def _refresh(self):
        if self.model.view is None:
            self.table.clear()
            self.plot.clear()
            self.count_lbl.configure(text="")
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

        self._set_stats(shown_df, shown, total)
        self.table.set_dataframe(shown_df)

    def _on_select(self, _evt=None):
        if self._plot_provider is None:
            return
        sel = self.table.tree.selection()
        if not sel:
            return
        item = sel[0]
        values = self.table.tree.item(item, "values")
        cols = list(self.table.tree["columns"])
        row = dict(zip(cols, values))
        try:
            pdata = self._plot_provider(row)
            if pdata is not None:
                self.plot.set_data(pdata)
        except Exception as e:
            self.on_log(f"Plot error: {e}")
