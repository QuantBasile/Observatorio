
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import pandas as pd

from .data_table import DataTable


class UnderlyingsTab(ttk.Frame):
    """
    First (and currently only) tab: shows a DataFrame in a table.
    """
    def __init__(self, parent: tk.Misc):
        super().__init__(parent, style="Panel.TFrame")

        header = ttk.Frame(self, style="Panel.TFrame")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        header.columnconfigure(0, weight=1)

        self.title_lbl = ttk.Label(header, text="Underlyings", style="Title.TLabel")
        self.title_lbl.grid(row=0, column=0, sticky="w")

        self.count_lbl = ttk.Label(header, text="", style="Muted.TLabel")
        self.count_lbl.grid(row=0, column=1, sticky="e")

        self.table = DataTable(self)
        self.table.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

    def set_dataframe(self, df: pd.DataFrame):
        self.count_lbl.configure(text=f"{len(df):,} rows × {df.shape[1]} cols")
        self.table.set_dataframe(df)
