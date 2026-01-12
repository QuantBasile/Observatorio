
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
import pandas as pd

from ..theme import Theme
from ..data.model import DataModel
from ..data.state import PipelineState
from ..actions.registry import ActionSpec, get_default_actions
from .logger import TextLogger
from .styles import apply_futuristic_style
from .data_view import DataView
from .spread_matrix_view import SpreadMatrixView
from .table_plot_view import TablePlotView
from .plot_canvas import PlotData, Series


class MainWindow(tk.Tk):
    def __init__(self, on_load_underlying, on_load_raptor, actions: list[ActionSpec] | None = None):
        super().__init__()
        self.title("Underlying App")
        self.geometry("1600x940")

        Theme.apply(self)
        apply_futuristic_style(self)

        self.state = PipelineState()

        self._underlyings_df: pd.DataFrame | None = None
        self._raptor_df: pd.DataFrame | None = None
        self._action_dfs: dict[str, pd.DataFrame] = {}

        self.actions: list[ActionSpec] = actions or get_default_actions()

        # Top bar
        self.top = ttk.Frame(self, style="Topbar.TFrame")
        self.top.pack(side="top", fill="x")

        self.load_under_btn = ttk.Button(self.top, text="Load Underlying", style="Accent.TButton", command=on_load_underlying)
        self.load_under_btn.pack(side="left", padx=(12, 8), pady=10)

        self.load_raptor_btn = ttk.Button(self.top, text="Load Raptor", style="Accent.TButton", command=on_load_raptor)
        self.load_raptor_btn.pack(side="left", padx=(0, 12), pady=10)
        self.load_raptor_btn.state(["disabled"])

        ttk.Separator(self.top, orient="vertical").pack(side="left", fill="y", padx=10, pady=10)

        self.action_buttons: dict[str, ttk.Button] = {}
        for a in self.actions:
            b = ttk.Button(self.top, text=a.button_text, style="Calc.TButton", command=lambda aa=a: self.run_action(aa))
            b.pack(side="left", padx=6, pady=10)
            b.state(["disabled"])
            self.action_buttons[a.key] = b

        self.top_spacer = ttk.Frame(self.top, style="Topbar.TFrame")
        self.top_spacer.pack(side="left", fill="x", expand=True)

        self.run_all_btn = ttk.Button(self.top, text="Run all ▶", style="Calc.TButton", command=self.run_all)
        self.run_all_btn.pack(side="right", padx=12, pady=10)

        # Status bar
        self.status = ttk.Frame(self, style="Topbar.TFrame")
        self.status.pack(side="top", fill="x")

        self._status_labels: dict[str, ttk.Label] = {}
        self._status_labels["underlyings"] = ttk.Label(self.status, text="Underlyings: ⬤ not loaded", style="Muted.TLabel")
        self._status_labels["underlyings"].pack(side="left", padx=(12, 16), pady=(0, 8))
        self._status_labels["raptor"] = ttk.Label(self.status, text="Raptor: ⬤ not loaded", style="Muted.TLabel")
        self._status_labels["raptor"].pack(side="left", padx=(0, 16), pady=(0, 8))

        for a in self.actions:
            key = f"status_{a.key}"
            lbl = ttk.Label(self.status, text=f"{a.name}: ⬤ not ready", style="Muted.TLabel")
            lbl.pack(side="left", padx=(0, 16), pady=(0, 8))
            self._status_labels[key] = lbl

        # Middle split
        self.middle = ttk.Frame(self, style="App.TFrame")
        self.middle.pack(side="top", fill="both", expand=True)
        self.middle.columnconfigure(1, weight=1)
        self.middle.rowconfigure(0, weight=1)

        # Navigation
        self.nav = ttk.Frame(self.middle, style="Nav.TFrame", width=270)
        self.nav.grid(row=0, column=0, sticky="nsw")
        self.nav.grid_propagate(False)

        ttk.Label(self.nav, text="Navigation", style="Muted.TLabel").pack(anchor="w", padx=12, pady=(12, 8))
        ttk.Button(self.nav, text="Underlyings", style="Nav.TButton", command=self.show_underlyings).pack(fill="x", padx=10, pady=(0, 6))
        ttk.Button(self.nav, text="Raptor", style="Nav.TButton", command=self.show_raptor).pack(fill="x", padx=10, pady=(0, 6))

        ttk.Separator(self.nav, orient="horizontal").pack(fill="x", padx=10, pady=12)

        self.nav_action_buttons: dict[str, ttk.Button] = {}
        for a in self.actions:
            b = ttk.Button(self.nav, text=a.name, style="Nav.TButton", command=lambda aa=a: self.show_action(aa))
            b.pack(fill="x", padx=10, pady=(0, 6))
            self.nav_action_buttons[a.key] = b

        # Content
        self.content = ttk.Frame(self.middle, style="Panel.TFrame")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        # Log
        self.log_frame = ttk.Frame(self, style="Log.TFrame")
        self.log_frame.pack(side="bottom", fill="x")
        ttk.Label(self.log_frame, text="Log", style="Muted.TLabel").pack(anchor="w", padx=12, pady=(8, 0))
        self.log_text = tk.Text(
            self.log_frame, height=6, wrap="word",
            bg="#ffffff", fg="#12223a", insertbackground="#12223a",
            relief="flat", highlightthickness=1, highlightbackground="#d2d9ea"
        )
        self.log_text.pack(fill="both", expand=False, padx=12, pady=(4, 12))
        self.logger = TextLogger(self.log_text)

        # Models + base views
        self.model_under = DataModel()
        self.model_raptor = DataModel()

        self.under_view = DataView(
            self.content,
            title="Underlyings",
            model=self.model_under,
            on_log=self.logger.log,
            row_limit=None,
            enable_filters=True,
            show_stats=True,
            header_buttons=[
                {"text": "Next 7d", "command": self._toggle_underlyings_next_week, "style": "TButton"},
            ],
        )
        # manual search apply for huge DF
        self.raptor_view = DataView(self.content, title="Raptor", model=self.model_raptor, on_log=self.logger.log, row_limit=500, enable_filters=True, show_stats=True, manual_search_apply=True)

        # Action views
        self.action_views: dict[str, tk.Widget] = {}
        for a in self.actions:
            if a.view_type == "spread_matrix":
                self.action_views[a.key] = SpreadMatrixView(self.content, title=a.view_title, on_log=self.logger.log)
            elif a.view_type == "table_plot":
                v = TablePlotView(self.content, title=a.view_title, on_log=self.logger.log, row_limit=a.row_limit or 2000)
                v.set_plot_provider(self._issuer_plot_provider)
                self.action_views[a.key] = v
            else:
                m = DataModel()
                self.action_views[a.key] = DataView(self.content, title=a.view_title, model=m, on_log=self.logger.log, row_limit=a.row_limit, enable_filters=a.enable_filters, show_stats=True)

        self._current_view: tk.Widget | None = None
        self.show_underlyings()
        self.logger.log("App started. Tip: Load Underlying → Load Raptor → Run all ▶")
        self._refresh_pipeline_ui()

    # --- view switching ---
    def _show_view(self, view: tk.Widget):
        if self._current_view is not None:
            self._current_view.grid_forget()
        self._current_view = view
        self._current_view.grid(row=0, column=0, sticky="nsew")

    def show_underlyings(self): self._show_view(self.under_view)
    def show_raptor(self): self._show_view(self.raptor_view)

    def show_action(self, action: ActionSpec):
        self._show_view(self.action_views[action.key])

    # --- quick filter buttons ---
    def run_action(self, action: ActionSpec):
        """Run one action and display its view.

        - For spread_matrix: just attach current raptor df and recompute.
        - For table/table_plot: compute df_out = action.run(raptor_df) and set it on the view.
        """
        try:
            if self._raptor_df is None or self._raptor_df.empty:
                self.logger.log(f"{action.name}: needs Raptor. Click 'Load Raptor' first.")
                messagebox.showinfo(action.name, "Please click 'Load Raptor' first.")
                return

            view = self.action_views.get(action.key)
            if view is None:
                self.logger.log(f"No view registered for action: {action.key}")
                return

            # Spread matrix uses the full raptor df directly
            if action.view_type == "spread_matrix":
                try:
                    view.set_raptor(self._raptor_df)
                except Exception as e:
                    self.logger.log(f"Spread matrix error: {e}")
                self.show_action(action)
                return

            # Compute output dataframe for table/table_plot actions
            out = action.run(self._raptor_df)
            if out is None:
                self.logger.log(f"{action.name}: returned None")
                return
            if isinstance(out, pd.DataFrame):
                df_out = out
            else:
                # allow actions to return anything convertible to DataFrame (list of dicts, etc.)
                df_out = pd.DataFrame(out)

            self._action_dfs[action.key] = df_out

            # Push into view
            if hasattr(view, "set_dataframe"):
                view.set_dataframe(df_out)

            self.show_action(action)
            self.logger.log(f"{action.name}: done ({len(df_out)} rows)")
        except Exception as e:
            self.logger.log(f"Action error ({action.key}): {e}")
            messagebox.showerror("Action error", str(e))

    def _toggle_underlyings_next_week(self):
        """Toggle a quick filter: keep only underlyings with EventNext within the next 7 days."""
        # If already active -> clear
        if getattr(self.model_under, "quick_filter_label", "") == "next_7d":
            self.under_view.clear_quick_filter()
            self.logger.log("Quick filter cleared: next 7 days")
            return

        def _fn(df: pd.DataFrame) -> pd.DataFrame:
            col = "EventNext" if "EventNext" in df.columns else ("Maturity" if "Maturity" in df.columns else ("maturity" if "maturity" in df.columns else None))
            if col is None:
                return df
            t = pd.to_datetime(df[col], errors="coerce")
            now = pd.Timestamp.now()
            end = now + pd.Timedelta(days=7)
            return df[(t >= now) & (t <= end)]

        self.under_view.set_quick_filter(_fn, label="next_7d")
        self.logger.log("Quick filter applied: EventNext within next 7 days")
        self.logger.log("Quick filter applied: Underlyings in next 7 days")

    # --- pipeline setters ---
    def set_underlyings_df(self, df: pd.DataFrame):
        self._underlyings_df = df
        self.state.mark_underlyings_loaded()
        self.under_view.set_dataframe(df)
        self.load_raptor_btn.state(["!disabled"])
        self.logger.log(f"Loaded underlyings: {len(df):,} rows × {df.shape[1]} cols.")
        self._refresh_pipeline_ui()

    def set_raptor_df(self, df: pd.DataFrame):
        self._raptor_df = df
        self.state.mark_raptor_loaded()
        self.raptor_view.set_dataframe(df)
        self.logger.log(f"Loaded raptor: {len(df):,} rows × {df.shape[1]} cols. (UI shows first 500)")
        for b in self.action_buttons.values():
            b.state(["!disabled"])
        self._refresh_pipeline_ui()

    def get_underlyings_df(self) -> pd.DataFrame | None:
        return self._underlyings_df

    def get_raptor_df(self) -> pd.DataFrame | None:
        return self._raptor_df

    # --- status / stale ---
    def _refresh_pipeline_ui(self):
        self._status_labels["underlyings"].configure(text="Underlyings: 🟢 loaded" if self.state.is_underlyings_loaded() else "Underlyings: ⬤ not loaded")
        self._status_labels["raptor"].configure(text="Raptor: 🟢 loaded" if self.state.is_raptor_loaded() else "Raptor: ⬤ not loaded")

        for a in self.actions:
            status_key = f"status_{a.key}"
            nav_btn = self.nav_action_buttons[a.key]
            if not self.state.is_action_ready(a.key):
                self._status_labels[status_key].configure(text=f"{a.name}: ⬤ not ready")
                nav_btn.configure(text=a.name)
            else:
                if self.state.is_action_stale(a.key):
                    self._status_labels[status_key].configure(text=f"{a.name}: ⚠ stale")
                    nav_btn.configure(text=f"{a.name}  ⚠")
                else:
                    self._status_labels[status_key].configure(text=f"{a.name}: 🟢 ready")
                    nav_btn.configure(text=a.name)

    def _guard_raptor(self) -> pd.DataFrame | None:
        if self._raptor_df is None or self._raptor_df.empty:
            self.logger.log("Raptor not loaded. Please load Raptor first.")
            messagebox.showinfo("Missing data", "Load Raptor first.")
            return None
        return self._raptor_df


    # --- plot provider for Issuer Plot action
    def _issuer_plot_provider(self, row: dict):
        """Plot provider for the 'Issuer Plot' view.

        SIMPLE BEHAVIOR:
          - plot Sized_GAP_Ask (y) vs Strike (x)
          - filter to the same Issuer + Type + Maturity + Underlying as the selected row
          - highlight the selected point
        """
        df = self._raptor_df
        if df is None or df.empty:
            return None

        # Required columns
        if "Strike" not in df.columns or "Sized_GAP_Ask" not in df.columns:
            return None

        # Canonical columns (with legacy fallbacks)
        issuer_col = "Issuer" if "Issuer" in df.columns else ("issuer" if "issuer" in df.columns else ("ISSUER" if "ISSUER" in df.columns else None))
        type_col = "Type" if "Type" in df.columns else ("product" if "product" in df.columns else None)
        mat_col = "Maturity" if "Maturity" in df.columns else ("maturity" if "maturity" in df.columns else None)
        # User's Raptor uses underlying_isin
        und_col = "underlying_isin" if "underlying_isin" in df.columns else None

        if None in (issuer_col, type_col, mat_col, und_col):
            return None

        sel_issuer = row.get("Issuer") or row.get("issuer") or row.get("ISSUER")
        sel_type = row.get("Type") or row.get("product")
        sel_mat = row.get("Maturity") or row.get("maturity")
        sel_und = row.get("underlying_isin")

        if None in (sel_issuer, sel_type, sel_mat, sel_und):
            return None

        # IMPORTANT: maturity often renders differently when cast to string
        # (e.g. '2024-02-26T00:00:00.000000000' vs '2024-02-26 00:00:00').
        # Use datetime comparison instead of raw string equality.
        mat_series = pd.to_datetime(df[mat_col], errors="coerce")
        try:
            # if tz-aware
            if getattr(mat_series.dt, "tz", None) is not None:
                mat_series = mat_series.dt.tz_convert(None)
        except Exception:
            pass

        sel_mat_dt = pd.to_datetime(sel_mat, errors="coerce")
        if pd.isna(sel_mat_dt):
            return None
        try:
            if getattr(sel_mat_dt, "tzinfo", None) is not None:
                sel_mat_dt = sel_mat_dt.tz_convert(None)
        except Exception:
            pass

        mask = (
            (df[issuer_col].astype("string") == str(sel_issuer))
            & (df[type_col].astype("string") == str(sel_type))
            & (mat_series == sel_mat_dt)
            & (df[und_col].astype("string") == str(sel_und))
        )

        sub = df.loc[mask, ["Strike", "Sized_GAP_Ask"]].dropna()
        if sub.empty:
            return None

        # Downsample (fast): keep at most ~2000 points
        maxn = 2000
        if len(sub) > maxn:
            step = max(1, len(sub) // maxn)
            sub = sub.iloc[::step, :]

        series = [
            Series(
                label=f"{sel_issuer} | {sel_type} | {sel_mat} | {sel_und}",
                x=sub["Strike"].to_numpy(),
                y=sub["Sized_GAP_Ask"].to_numpy(),
                color="#2563eb",  # blue
                marker="o",
            )
        ]

        # Highlight selected row point
        hx = row.get("Strike")
        hy = row.get("Sized_GAP_Ask")
        highlight = None
        if hx is not None and hy is not None:
            try:
                highlight = {"x": float(hx), "y": float(hy)}
            except Exception:
                highlight = None

        return PlotData(series=series, title="Sized_GAP_Ask vs Strike", highlight=highlight)


    def run_all(self):
        self.logger.log("Run all ▶ starting…")
        if self._underlyings_df is None:
            self.logger.log("Run all ▶ needs Underlyings. Click 'Load Underlying' first.")
            messagebox.showinfo("Run all", "Please click 'Load Underlying' first.\nThen click 'Run all ▶' again.")
            return
        if self._raptor_df is None:
            self.logger.log("Run all ▶ needs Raptor. Click 'Load Raptor' first.")
            messagebox.showinfo("Run all", "Please click 'Load Raptor' first.\nThen click 'Run all ▶' again.")
            return

        for a in self.actions:
            self.run_action(a)

        self.logger.log("Run all ▶ done. ✨")