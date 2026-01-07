import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass
from datetime import datetime, timedelta, date
import numpy as np
import pandas as pd
import random
import string

# -----------------------------
# Utilities: logging to Text
# -----------------------------
class TextLogger:
    def __init__(self, text_widget: tk.Text):
        self.text = text_widget
        self.text.configure(state="disabled")

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        self.text.configure(state="normal")
        self.text.insert("end", line)
        self.text.see("end")
        self.text.configure(state="disabled")


# -----------------------------
# Data layer
# -----------------------------
@dataclass
class FilterSpec:
    column: str
    op: str
    value1: str = ""
    value2: str = ""  # used for "between"


class DataModel:
    """
    Holds the raw dataframe and the filtered view.
    Filtering is designed to be general: it tries numeric, datetime, and fallback to string.
    """
    def __init__(self, logger: TextLogger | None = None):
        self.df: pd.DataFrame | None = None
        self.view: pd.DataFrame | None = None
        self.filters: list[FilterSpec] = []
        self.logger = logger

    def set_df(self, df: pd.DataFrame):
        self.df = df
        self.filters = []
        self.apply_filters()

    def apply_filters(self):
        if self.df is None:
            self.view = None
            return

        df = self.df.copy()
        for f in self.filters:
            if f.column not in df.columns:
                continue
            try:
                df = self._apply_single_filter(df, f)
            except Exception as e:
                if self.logger:
                    self.logger.log(f"Filter failed on {f.column} {f.op}: {e}")
        self.view = df

    def add_filter(self, spec: FilterSpec):
        self.filters.append(spec)
        self.apply_filters()

    def clear_filters(self):
        self.filters = []
        self.apply_filters()

    def remove_filter_at(self, idx: int):
        if 0 <= idx < len(self.filters):
            self.filters.pop(idx)
            self.apply_filters()

    def _apply_single_filter(self, df: pd.DataFrame, f: FilterSpec) -> pd.DataFrame:
        s = df[f.column]

        op = f.op
        v1 = (f.value1 or "").strip()
        v2 = (f.value2 or "").strip()

        # helpers
        def try_to_numeric(x: str):
            try:
                return float(x)
            except Exception:
                return None

        def try_to_datetime(x: str):
            # Accept flexible inputs: "2026-01-07", "07.01.2026", "2026/01/07", etc.
            try:
                return pd.to_datetime(x, errors="raise")
            except Exception:
                return None

        # Null ops
        if op == "is null":
            return df[s.isna()]
        if op == "is not null":
            return df[~s.isna()]

        # Try numeric compare if possible
        num_v1 = try_to_numeric(v1)
        num_v2 = try_to_numeric(v2) if v2 else None

        # Try datetime compare if possible (and if series looks datetime-like or v parses)
        dt_v1 = try_to_datetime(v1)
        dt_v2 = try_to_datetime(v2) if v2 else None

        is_series_datetime = pd.api.types.is_datetime64_any_dtype(s)

        # Decide comparison mode:
        # 1) if series is datetime OR value parses as datetime and series convertible => datetime mode
        # 2) else if value parses numeric and series numeric-ish => numeric mode
        # 3) else string mode
        datetime_mode = False
        if is_series_datetime:
            datetime_mode = True
        elif dt_v1 is not None:
            # attempt to convert series to datetime (non-destructive via temporary)
            tmp = pd.to_datetime(s, errors="coerce")
            if tmp.notna().any():
                s = tmp
                datetime_mode = True

        if datetime_mode:
            if dt_v1 is None and op not in ("contains", "startswith", "endswith"):
                # can't compare
                return df.iloc[0:0]

            if op == "=":
                return df[s.dt.date == dt_v1.date()]
            if op == "!=":
                return df[s.dt.date != dt_v1.date()]
            if op == "<":
                return df[s < dt_v1]
            if op == "<=":
                return df[s <= dt_v1]
            if op == ">":
                return df[s > dt_v1]
            if op == ">=":
                return df[s >= dt_v1]
            if op == "between":
                if dt_v2 is None:
                    return df.iloc[0:0]
                lo, hi = (dt_v1, dt_v2) if dt_v1 <= dt_v2 else (dt_v2, dt_v1)
                return df[(s >= lo) & (s <= hi)]

            # fallback to string-type ops on datetime as formatted
            s_str = s.dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")
            return self._apply_string_ops(df, s_str, op, v1)

        # numeric mode?
        if num_v1 is not None:
            s_num = pd.to_numeric(s, errors="coerce")
            if s_num.notna().any():
                if op == "=":
                    return df[s_num == num_v1]
                if op == "!=":
                    return df[s_num != num_v1]
                if op == "<":
                    return df[s_num < num_v1]
                if op == "<=":
                    return df[s_num <= num_v1]
                if op == ">":
                    return df[s_num > num_v1]
                if op == ">=":
                    return df[s_num >= num_v1]
                if op == "between":
                    if num_v2 is None:
                        return df.iloc[0:0]
                    lo, hi = (num_v1, num_v2) if num_v1 <= num_v2 else (num_v2, num_v1)
                    return df[(s_num >= lo) & (s_num <= hi)]
                # string ops on numeric as text
                s_str = s_num.map(lambda x: "" if pd.isna(x) else str(x))
                return self._apply_string_ops(df, s_str, op, v1)

        # string mode
        s_str = s.astype("string").fillna("")
        return self._apply_string_ops(df, s_str, op, v1)

    def _apply_string_ops(self, df: pd.DataFrame, s_str: pd.Series, op: str, v1: str) -> pd.DataFrame:
        needle = v1
        if op == "=":
            return df[s_str == needle]
        if op == "!=":
            return df[s_str != needle]
        if op == "contains":
            return df[s_str.str.contains(needle, case=False, na=False)]
        if op == "startswith":
            return df[s_str.str.startswith(needle)]
        if op == "endswith":
            return df[s_str.str.endswith(needle)]
        # unsupported => no-op
        return df


# -----------------------------
# Fake data generator
# -----------------------------
def _rand_isin():
    # simplistic fake ISIN: 2 letters + 10 alnum
    cc = random.choice(["DE", "FR", "ES", "NL", "IT", "US", "GB"])
    body = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
    return cc + body

def _rand_wkn():
    # German WKN is usually 6 chars
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

def make_fake_underlyings(n_rows=700, seed=42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    sectors = ["Tech", "Industrials", "Financials", "Healthcare", "Energy", "Consumer", "Utilities"]
    countries = ["DE", "FR", "ES", "NL", "IT", "US", "GB"]
    currencies = ["EUR", "USD", "GBP"]
    ratings = ["AAA", "AA", "A", "BBB", "BB", "B"]

    today = pd.Timestamp(date.today())

    # EventNext: some today, some future/past nearby
    # Make ~4% of rows "today"
    offsets = rng.integers(-20, 60, size=n_rows)
    event_next = today + pd.to_timedelta(offsets, unit="D") + pd.to_timedelta(rng.integers(0, 24, size=n_rows), unit="h")
    mask_today = rng.random(n_rows) < 0.04
    event_next[mask_today] = today + pd.to_timedelta(rng.integers(6, 18, size=mask_today.sum()), unit="h")

    df = pd.DataFrame({
        "isin": [_rand_isin() for _ in range(n_rows)],
        "wkn":  [_rand_wkn() for _ in range(n_rows)],
        "name": [f"Company {i:04d}" for i in range(1, n_rows + 1)],
        "sector": rng.choice(sectors, size=n_rows),
        "country": rng.choice(countries, size=n_rows),
        "currency": rng.choice(currencies, size=n_rows),
        "px_last": np.round(rng.lognormal(mean=3.6, sigma=0.35, size=n_rows), 2),
        "mkt_cap_bn": np.round(rng.lognormal(mean=2.0, sigma=0.7, size=n_rows), 2),
        "vol_20d": np.round(rng.uniform(0.10, 0.80, size=n_rows), 4),
        "beta_1y": np.round(rng.normal(1.0, 0.35, size=n_rows), 3),
        "pe_fwd": np.round(rng.uniform(5, 35, size=n_rows), 2),
        "div_yield": np.round(rng.uniform(0.0, 0.08, size=n_rows), 4),
        "eps_ttm": np.round(rng.normal(4.0, 2.0, size=n_rows), 2),
        "rev_ttm_bn": np.round(rng.lognormal(mean=1.4, sigma=0.8, size=n_rows), 2),
        "iv_30d": np.round(rng.uniform(0.12, 1.10, size=n_rows), 4),
        "option_liq_score": rng.integers(1, 101, size=n_rows),
        "EventNext": pd.to_datetime(event_next),
        "EventChange": np.round(rng.uniform(0.01, 0.12, size=n_rows), 4),  # expected move rel, 0.03 => 3%
        "updated_at": pd.Timestamp.now().floor("s"),
        "note": rng.choice(["", "Watch", "Earnings", "Dividend", "Split"], size=n_rows, p=[0.75, 0.10, 0.08, 0.05, 0.02]),
    })

    # Ensure 20 columns (we already have 20)
    return df


# -----------------------------
# UI components
# -----------------------------
class DataTable(ttk.Frame):
    """
    A Treeview-based table that can render any DataFrame.
    Highlights rows where EventNext is today (date match).
    """
    def __init__(self, parent, logger: TextLogger):
        super().__init__(parent)
        self.logger = logger

        self.tree = ttk.Treeview(self, columns=(), show="headings")
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Tag for "today"
        self.tree.tag_configure("event_today", background="#fff2cc")  # soft highlight

        # store current df
        self._df: pd.DataFrame | None = None

    def set_dataframe(self, df: pd.DataFrame):
        self._df = df
        self._rebuild_columns(df.columns.tolist())
        self._populate_rows(df)

    def clear(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._df = None

    def _rebuild_columns(self, columns: list[str]):
        # clear old
        self.tree["columns"] = columns
        for col in columns:
            self.tree.heading(col, text=col)
            # simple width heuristic; user can resize manually
            self.tree.column(col, width=max(90, min(220, 9 * len(col))), anchor="w")

    def _populate_rows(self, df: pd.DataFrame):
        # clear old rows
        for item in self.tree.get_children():
            self.tree.delete(item)

        if df is None or df.empty:
            return

        # Highlight logic: if there's EventNext column and it's datetime-like
        today = date.today()
        has_eventnext = "EventNext" in df.columns

        # Insert rows
        # NOTE: Treeview needs strings; keep datetimes readable
        for _, row in df.iterrows():
            values = []
            tags = ()
            for col in df.columns:
                val = row[col]
                if isinstance(val, (pd.Timestamp, datetime)):
                    val = pd.to_datetime(val).strftime("%Y-%m-%d %H:%M:%S")
                values.append("" if pd.isna(val) else str(val))

            if has_eventnext:
                try:
                    ev = row["EventNext"]
                    ev_dt = pd.to_datetime(ev, errors="coerce")
                    if pd.notna(ev_dt) and ev_dt.date() == today:
                        tags = ("event_today",)
                except Exception:
                    pass

            self.tree.insert("", "end", values=values, tags=tags)


class FilterPanel(ttk.LabelFrame):
    """
    General filter builder: select column + operator + value(s).
    Supports stacking multiple filters.
    """
    OPS = ["=", "!=", "<", "<=", ">", ">=", "between", "contains", "startswith", "endswith", "is null", "is not null"]

    def __init__(self, parent, model: DataModel, on_change, logger: TextLogger):
        super().__init__(parent, text="Filters")
        self.model = model
        self.on_change = on_change
        self.logger = logger

        self.col_var = tk.StringVar()
        self.op_var = tk.StringVar(value="contains")
        self.v1_var = tk.StringVar()
        self.v2_var = tk.StringVar()

        # Top row: selectors
        ttk.Label(self, text="Column").grid(row=0, column=0, sticky="w", padx=6, pady=(6, 2))
        self.col_cb = ttk.Combobox(self, textvariable=self.col_var, state="readonly", width=28)
        self.col_cb.grid(row=1, column=0, sticky="ew", padx=6)

        ttk.Label(self, text="Op").grid(row=0, column=1, sticky="w", padx=6, pady=(6, 2))
        self.op_cb = ttk.Combobox(self, textvariable=self.op_var, values=self.OPS, state="readonly", width=14)
        self.op_cb.grid(row=1, column=1, sticky="ew", padx=6)
        self.op_cb.bind("<<ComboboxSelected>>", self._on_op_changed)

        ttk.Label(self, text="Value").grid(row=0, column=2, sticky="w", padx=6, pady=(6, 2))
        self.v1_entry = ttk.Entry(self, textvariable=self.v1_var, width=22)
        self.v1_entry.grid(row=1, column=2, sticky="ew", padx=6)

        ttk.Label(self, text="And").grid(row=0, column=3, sticky="w", padx=6, pady=(6, 2))
        self.v2_entry = ttk.Entry(self, textvariable=self.v2_var, width=22)
        self.v2_entry.grid(row=1, column=3, sticky="ew", padx=6)

        self.add_btn = ttk.Button(self, text="Add filter", command=self._add_filter)
        self.add_btn.grid(row=1, column=4, padx=6, sticky="ew")

        self.clear_btn = ttk.Button(self, text="Clear all", command=self._clear_all)
        self.clear_btn.grid(row=1, column=5, padx=(0, 6), sticky="ew")

        # Active filters list
        ttk.Label(self, text="Active filters (double-click to remove)").grid(row=2, column=0, columnspan=6, sticky="w", padx=6, pady=(8, 2))
        self.listbox = tk.Listbox(self, height=4)
        self.listbox.grid(row=3, column=0, columnspan=6, sticky="nsew", padx=6, pady=(0, 6))
        self.listbox.bind("<Double-Button-1>", self._remove_selected)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._on_op_changed()  # initial enable/disable

    def set_columns(self, columns: list[str]):
        self.col_cb["values"] = columns
        if columns and not self.col_var.get():
            self.col_var.set(columns[0])

    def refresh_active_filters(self):
        self.listbox.delete(0, "end")
        for f in self.model.filters:
            if f.op == "between":
                s = f"{f.column} {f.op} {f.value1} and {f.value2}"
            elif f.op in ("is null", "is not null"):
                s = f"{f.column} {f.op}"
            else:
                s = f"{f.column} {f.op} {f.value1}"
            self.listbox.insert("end", s)

    def _on_op_changed(self, *_):
        op = self.op_var.get()
        if op == "between":
            self.v1_entry.configure(state="normal")
            self.v2_entry.configure(state="normal")
        elif op in ("is null", "is not null"):
            self.v1_entry.configure(state="disabled")
            self.v2_entry.configure(state="disabled")
        else:
            self.v1_entry.configure(state="normal")
            self.v2_entry.configure(state="disabled")
            self.v2_var.set("")

    def _add_filter(self):
        if self.model.df is None:
            messagebox.showinfo("No data", "Load data first.")
            return
        col = self.col_var.get()
        op = self.op_var.get()

        if not col:
            return

        if op == "between":
            if not self.v1_var.get().strip() or not self.v2_var.get().strip():
                messagebox.showwarning("Missing values", "For 'between' you need Value and And.")
                return
            spec = FilterSpec(col, op, self.v1_var.get(), self.v2_var.get())
        elif op in ("is null", "is not null"):
            spec = FilterSpec(col, op, "", "")
        else:
            if not self.v1_var.get().strip():
                messagebox.showwarning("Missing value", "Please enter a Value.")
                return
            spec = FilterSpec(col, op, self.v1_var.get(), "")

        self.model.add_filter(spec)
        self.logger.log(f"Added filter: {col} {op}")
        self.refresh_active_filters()
        self.on_change()

    def _clear_all(self):
        self.model.clear_filters()
        self.logger.log("Cleared all filters")
        self.refresh_active_filters()
        self.on_change()

    def _remove_selected(self, _evt=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.model.remove_filter_at(idx)
        self.logger.log(f"Removed filter #{idx + 1}")
        self.refresh_active_filters()
        self.on_change()


class UnderlyingTab(ttk.Frame):
    """
    First tab: filter panel + table.
    """
    def __init__(self, parent, model: DataModel, logger: TextLogger):
        super().__init__(parent)
        self.model = model
        self.logger = logger

        self.filter_panel = FilterPanel(self, model=self.model, on_change=self._refresh_table, logger=self.logger)
        self.filter_panel.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))

        self.table = DataTable(self, logger=self.logger)
        self.table.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 8))

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def on_data_loaded(self):
        if self.model.df is None:
            self.table.clear()
            return
        cols = list(self.model.df.columns)
        self.filter_panel.set_columns(cols)
        self.filter_panel.refresh_active_filters()
        self._refresh_table()

    def _refresh_table(self):
        if self.model.view is None:
            self.table.clear()
            return
        self.table.set_dataframe(self.model.view)


class NavigationPanel(ttk.Frame):
    """
    Left navigation with tabs (Notebook).
    We'll keep it simple: a Notebook in the left panel.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)


class TopBar(ttk.Frame):
    def __init__(self, parent, on_load_underlying):
        super().__init__(parent)
        self.on_load_underlying = on_load_underlying

        self.load_btn = ttk.Button(self, text="Load Underlying", command=self.on_load_underlying)
        self.load_btn.pack(side="left", padx=8, pady=6)

        # space for future buttons
        self.spacer = ttk.Label(self, text="")
        self.spacer.pack(side="left", fill="x", expand=True)


class LogPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        ttk.Label(self, text="Log").pack(anchor="w", padx=8, pady=(6, 0))
        self.text = tk.Text(self, height=7, wrap="word")
        self.text.pack(fill="both", expand=True, padx=8, pady=(0, 8))


# -----------------------------
# Main app
# -----------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Underlying Viewer (Tkinter + Pandas)")
        self.geometry("1400x850")

        # Layout: Top / Middle / Bottom
        self.top = TopBar(self, on_load_underlying=self.load_underlying)
        self.top.pack(side="top", fill="x")

        self.middle = ttk.Frame(self)
        self.middle.pack(side="top", fill="both", expand=True)

        self.bottom = LogPanel(self)
        self.bottom.pack(side="bottom", fill="x")

        self.logger = TextLogger(self.bottom.text)
        self.model = DataModel(logger=self.logger)

        # Middle split: left nav, right content
        self.middle.columnconfigure(1, weight=1)
        self.middle.rowconfigure(0, weight=1)

        self.nav = NavigationPanel(self.middle)
        self.nav.grid(row=0, column=0, sticky="nsw")

        self.content = ttk.Frame(self.middle)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.rowconfigure(0, weight=1)
        self.content.columnconfigure(0, weight=1)

        # Tabs inside nav; each tab can host a "page" in content.
        # For simplicity, we’ll put actual tab content in the main content area,
        # and keep the left notebook as the navigation.
        self.underlying_tab = UnderlyingTab(self.content, model=self.model, logger=self.logger)
        self.other_tab = ttk.Frame(self.content)
        ttk.Label(self.other_tab, text="(Tab placeholder)").pack(padx=20, pady=20)

        # Create nav tabs (left)
        self.nav_tab1 = ttk.Frame(self.nav.nb)
        self.nav_tab2 = ttk.Frame(self.nav.nb)
        self.nav.nb.add(self.nav_tab1, text="Underlyings")
        self.nav.nb.add(self.nav_tab2, text="Other")

        self.nav.nb.bind("<<NotebookTabChanged>>", self._on_nav_changed)

        # show default page
        self._show_page(self.underlying_tab)

        self.logger.log("App started.")

    def _show_page(self, frame: ttk.Frame):
        # clear content area
        for child in self.content.winfo_children():
            child.grid_forget()
        frame.grid(row=0, column=0, sticky="nsew")

    def _on_nav_changed(self, _evt=None):
        idx = self.nav.nb.index("current")
        if idx == 0:
            self._show_page(self.underlying_tab)
        else:
            self._show_page(self.other_tab)

    def load_underlying(self):
        """
        Loads fake data. Replace make_fake_underlyings(...) with your real loader later.
        """
        try:
            self.logger.log("Loading Underlying dataframe...")
            df = make_fake_underlyings(n_rows=700, seed=42)

            # Ensure required columns exist (as you requested)
            required = ["isin", "wkn", "name", "EventNext", "EventChange"]
            missing = [c for c in required if c not in df.columns]
            if missing:
                raise ValueError(f"Missing required columns: {missing}")

            self.model.set_df(df)
            self.underlying_tab.on_data_loaded()
            self.logger.log(f"Loaded dataframe: {len(df)} rows x {df.shape[1]} cols.")
        except Exception as e:
            self.logger.log(f"ERROR loading underlyings: {e}")
            messagebox.showerror("Load error", str(e))


if __name__ == "__main__":
    app = App()
    app.mainloop()
