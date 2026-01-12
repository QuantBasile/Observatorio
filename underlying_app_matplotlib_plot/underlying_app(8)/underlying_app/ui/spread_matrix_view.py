
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import pandas as pd

from .data_table import DataTable


class SpreadMatrixView(ttk.Frame):
    SHOW_LIMIT = 300

    def __init__(self, parent: tk.Misc, title: str, on_log):
        super().__init__(parent, style="Panel.TFrame")
        self.on_log = on_log
        self.title = title

        self._raptor: pd.DataFrame | None = None

        header = ttk.Frame(self, style="Panel.TFrame")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=title, style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.count_lbl = ttk.Label(header, text="", style="Muted.TLabel")
        self.count_lbl.grid(row=0, column=1, sticky="e")

        self.stats = ttk.Frame(self, style="Panel.TFrame")
        self.stats.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        self._stat_labels = [ttk.Label(self.stats, text="", style="Muted.TLabel") for _ in range(4)]
        for i, lbl in enumerate(self._stat_labels):
            lbl.grid(row=0, column=i, sticky="w", padx=(0 if i == 0 else 18, 0))

        self.filters = ttk.Frame(self, style="Panel.TFrame")
        self.filters.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))

        # Type
        prod_box = ttk.Frame(self.filters, style="Panel.TFrame")
        prod_box.grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Label(prod_box, text="Type", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(prod_box, text="[category/str]", style="Muted.TLabel").grid(row=0, column=1, sticky="w", padx=(6, 0))
        self.type_var = tk.StringVar(value="All")
        self.type_cb = ttk.Combobox(prod_box, textvariable=self.type_var, state="readonly", width=18, values=["All"])
        self.type_cb.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))

        # OptionType
        cp_box = ttk.Frame(self.filters, style="Panel.TFrame")
        cp_box.grid(row=0, column=1, padx=6, pady=6, sticky="w")
        ttk.Label(cp_box, text="OptionType", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(cp_box, text="[category/str]", style="Muted.TLabel").grid(row=0, column=1, sticky="w", padx=(6, 0))
        self.cp_var = tk.StringVar(value="All")
        self.cp_cb = ttk.Combobox(cp_box, textvariable=self.cp_var, state="readonly", width=18, values=["All", "Call", "Put"])
        self.cp_cb.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))

        # Maturity
        mat_box = ttk.Frame(self.filters, style="Panel.TFrame")
        mat_box.grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ttk.Label(mat_box, text="Maturity", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(mat_box, text="[datetime]", style="Muted.TLabel").grid(row=0, column=1, sticky="w", padx=(6, 0))
        self.mat_var = tk.StringVar(value="All")
        self.mat_cb = ttk.Combobox(mat_box, textvariable=self.mat_var, state="readonly", width=18, values=["All"])
        self.mat_cb.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))

        # apply
        apply_box = ttk.Frame(self.filters, style="Panel.TFrame")
        apply_box.grid(row=0, column=3, padx=6, pady=6, sticky="w")
        ttk.Label(apply_box, text=" ", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        self.apply_btn = ttk.Button(apply_box, text="Apply", style="Accent.TButton", command=self.recompute)
        self.apply_btn.grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.table = DataTable(self, on_copy=lambda t: self.on_log(f"Copied: {t}"))
        self.table.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.rowconfigure(3, weight=1)
        self.columnconfigure(0, weight=1)

    def set_raptor(self, raptor: pd.DataFrame):
        self._raptor = raptor
        type_col = self._col(raptor, "Type", ["product", "type"])
        if type_col:
            try:
                vals = raptor[type_col].astype("string").dropna().unique().tolist()
                vals = sorted([v for v in vals if v not in ("", "nan", "NaN", "<NA>")])
                self.type_cb.configure(values=["All"] + vals)
            except Exception:
                self.type_cb.configure(values=["All"])

        mat_col = self._col(raptor, "Maturity", ["maturity"])
        if mat_col:
            try:
                m = pd.to_datetime(raptor[mat_col], errors="coerce").dt.strftime("%Y-%m-%d")
                vals = pd.unique(m.dropna()).tolist()
                vals = sorted([v for v in vals if v not in ("", "nan", "NaN", "<NA>")])
                # Avoid insanely large dropdowns
                vals = vals[:3000]
                self.mat_cb.configure(values=["All"] + vals)
            except Exception:
                self.mat_cb.configure(values=["All"])
        self.recompute()

    def _col(self, df: pd.DataFrame, primary: str, fallbacks: list[str]) -> str | None:
        if primary in df.columns:
            return primary
        for f in fallbacks:
            if f in df.columns:
                return f
        return None

    def _find_bid_ask_cols(self, df: pd.DataFrame) -> tuple[str, str] | None:
        cols = set(df.columns)
        for b, a in [("Bid", "Ask"), ("bid", "ask"), ("px_bid", "px_ask")]:
            if b in cols and a in cols:
                return b, a
        return None

    def recompute(self):
        if self._raptor is None or self._raptor.empty:
            self.table.clear()
            self.count_lbl.configure(text="(load Raptor first)")
            return

        df = self._raptor
        total_rows = len(df)
        typ = self.type_var.get()
        cp = self.cp_var.get()
        mat_sel = self.mat_var.get()

        type_col = self._col(df, "Type", ["product", "type"])
        opt_col = self._col(df, "OptionType", ["callput", "type"])
        mat_col = self._col(df, "Maturity", ["maturity"])
        issuer_col = self._col(df, "Issuer", ["issuer", "ISSUER"])

        if typ != "All" and type_col:
            df = df[df[type_col].astype("string") == typ]
        if cp != "All":
            if opt_col:
                df = df[df[opt_col].astype("string") == cp]

        if mat_sel != "All" and mat_col:
            mstr = pd.to_datetime(df[mat_col], errors="coerce").dt.strftime("%Y-%m-%d")
            df = df[mstr == mat_sel]

        filtered_rows = len(df)

        key_col = None
        for k in ["underlying_isin", "underlying_wkn", "isin", "wkn"]:
            if k in df.columns:
                key_col = k
                break
        if key_col is None:
            key_col = df.columns[0]

        if issuer_col is None:
            out = pd.DataFrame({"info": ["Missing issuer column for matrix."]})
            self.table.set_dataframe(out)
            self.count_lbl.configure(text=f"total {total_rows:,} | filtered {filtered_rows:,}")
            return

        ba = self._find_bid_ask_cols(df)
        if ba is None:
            out = pd.DataFrame({"info": ["Missing Bid/Ask columns for matrix."]})
            self.table.set_dataframe(out)
            self.count_lbl.configure(text=f"total {total_rows:,} | filtered {filtered_rows:,}")
            return

        bid_col, ask_col = ba
        spread = (pd.to_numeric(df[ask_col], errors="coerce") - pd.to_numeric(df[bid_col], errors="coerce")).abs()
        tmp = df[[key_col, issuer_col]].copy()
        tmp["abs_spread"] = spread

        g = tmp.groupby([key_col, issuer_col], observed=True)["abs_spread"].mean().reset_index()
        mat_df = g.pivot(index=key_col, columns=issuer_col, values="abs_spread")

        mat_df["_avg"] = mat_df.mean(axis=1, skipna=True)
        mat_df = mat_df.sort_values("_avg", ascending=False).drop(columns=["_avg"])

        shown_rows = min(self.SHOW_LIMIT, len(mat_df))
        mat_show = mat_df.head(self.SHOW_LIMIT).round(6).reset_index()

        self.table.set_dataframe(mat_show)
        self.count_lbl.configure(text=f"total {total_rows:,} | filtered {filtered_rows:,} | showing {shown_rows:,} underlyings")
        self._stat_labels[0].configure(text=f"Underlyings shown: {shown_rows:,}")
        self._stat_labels[1].configure(text=f"Issuers: {mat_df.shape[1]:,}")
        self._stat_labels[2].configure(text=f"Filters: Type={typ}, OptionType={cp}, Maturity={mat_sel}")
        self._stat_labels[3].configure(text="Sort ▲▼ · dblclick copy · Ctrl+C")
