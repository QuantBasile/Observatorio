
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

import pandas as pd

from ..theme import Theme
from ..data.model import DataModel
from ..data.state import PipelineState
from ..data.actions_registry import ActionSpec, get_default_actions
from .logger import TextLogger
from .styles import apply_futuristic_style
from .data_view import DataView


class MainWindow(tk.Tk):
    def __init__(self, on_load_underlying, on_load_raptor, actions: list[ActionSpec] | None = None):
        super().__init__()
        self.title("Underlying App")
        self.geometry("1550x920")

        Theme.apply(self)
        apply_futuristic_style(self)

        self.state = PipelineState()

        # Data holders
        self._underlyings_df: pd.DataFrame | None = None
        self._raptor_df: pd.DataFrame | None = None
        self._action_dfs: dict[str, pd.DataFrame] = {}

        # Actions (plugin-ish)
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

        # Action buttons (auto-created)
        self.action_buttons: dict[str, ttk.Button] = {}
        for a in self.actions:
            b = ttk.Button(self.top, text=a.button_text, command=lambda aa=a: self.run_action(aa))
            b.pack(side="left", padx=6, pady=10)
            b.state(["disabled"])
            self.action_buttons[a.key] = b

        self.top_spacer = ttk.Frame(self.top, style="Topbar.TFrame")
        self.top_spacer.pack(side="left", fill="x", expand=True)

        self.run_all_btn = ttk.Button(self.top, text="Run all ▶", style="Accent.TButton", command=self.run_all)
        self.run_all_btn.pack(side="right", padx=12, pady=10)

        # Status bar (Pipeline state)  [IDEA #1]
        self.status = ttk.Frame(self, style="Topbar.TFrame")
        self.status.pack(side="top", fill="x")

        self._status_labels: dict[str, ttk.Label] = {}
        # Left-to-right: Underlyings, Raptor, Actions...
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
        self.nav = ttk.Frame(self.middle, style="Nav.TFrame", width=240)
        self.nav.grid(row=0, column=0, sticky="nsw")
        self.nav.grid_propagate(False)

        ttk.Label(self.nav, text="Navigation", style="Muted.TLabel").pack(anchor="w", padx=12, pady=(12, 8))

        self.nav_btn_underlyings = ttk.Button(self.nav, text="Underlyings", style="Nav.TButton", command=self.show_underlyings)
        self.nav_btn_underlyings.pack(fill="x", padx=10, pady=(0, 6))

        self.nav_btn_raptor = ttk.Button(self.nav, text="Raptor", style="Nav.TButton", command=self.show_raptor)
        self.nav_btn_raptor.pack(fill="x", padx=10, pady=(0, 6))

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

        # Bottom log
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

        # Models + Views
        self.model_under = DataModel()
        self.model_raptor = DataModel()
        self.model_actions: dict[str, DataModel] = {a.key: DataModel() for a in self.actions}

        self.under_view = DataView(self.content, title="Underlyings", model=self.model_under, on_log=self.logger.log, row_limit=None, enable_filters=True, show_stats=True)
        self.raptor_view = DataView(self.content, title="Raptor", model=self.model_raptor, on_log=self.logger.log, row_limit=500, enable_filters=True, show_stats=True)

        self.action_views: dict[str, DataView] = {}
        for a in self.actions:
            self.action_views[a.key] = DataView(
                self.content,
                title=a.view_title,
                model=self.model_actions[a.key],
                on_log=self.logger.log,
                row_limit=a.row_limit,
                enable_filters=a.enable_filters,   # False by default
                show_stats=True,
            )

        self._current_view: ttk.Frame | None = None
        self.show_underlyings()

        self.logger.log("App started. Tip: Load Underlying → Load Raptor → Run all ▶")
        self._refresh_pipeline_ui()

    # --- view switching ---
    def _show_view(self, view: ttk.Frame):
        if self._current_view is not None:
            self._current_view.grid_forget()
        self._current_view = view
        self._current_view.grid(row=0, column=0, sticky="nsew")

    def show_underlyings(self): self._show_view(self.under_view)
    def show_raptor(self): self._show_view(self.raptor_view)

    def show_action(self, action: ActionSpec):
        self._show_view(self.action_views[action.key])

    # --- setters used by app.py ---
    def set_underlyings_df(self, df: pd.DataFrame):
        self._underlyings_df = df
        self.state.mark_underlyings_loaded()
        self.under_view.set_dataframe(df)
        self.load_raptor_btn.state(["!disabled"])
        self.logger.log(f"Loaded underlyings: {len(df):,} rows × {df.shape[1]} cols.")
        self.show_underlyings()
        self._refresh_pipeline_ui()

    def set_raptor_df(self, df: pd.DataFrame):
        self._raptor_df = df
        self.state.mark_raptor_loaded()
        self.raptor_view.set_dataframe(df)
        self.logger.log(f"Loaded raptor: {len(df):,} rows × {df.shape[1]} cols. (UI shows first 500)")
        for b in self.action_buttons.values():
            b.state(["!disabled"])
        self.show_raptor()
        self._refresh_pipeline_ui()

    def get_underlyings_df(self) -> pd.DataFrame | None:
        return self._underlyings_df

    def get_raptor_df(self) -> pd.DataFrame | None:
        return self._raptor_df

    # --- stale/status UI (IDEA #1 + #2) ---
    def _refresh_pipeline_ui(self):
        # Underlyings
        if self.state.is_underlyings_loaded():
            self._status_labels["underlyings"].configure(text="Underlyings: 🟢 loaded")
        else:
            self._status_labels["underlyings"].configure(text="Underlyings: ⬤ not loaded")

        # Raptor
        if self.state.is_raptor_loaded():
            self._status_labels["raptor"].configure(text="Raptor: 🟢 loaded")
        else:
            self._status_labels["raptor"].configure(text="Raptor: ⬤ not loaded")

        # Actions
        for a in self.actions:
            key = a.key
            status_key = f"status_{key}"
            nav_btn = self.nav_action_buttons[key]

            if not self.state.is_action_ready(key):
                self._status_labels[status_key].configure(text=f"{a.name}: ⬤ not ready")
                nav_btn.configure(text=a.name)
            else:
                if self.state.is_action_stale(key):
                    # stale
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

    # --- run actions (plugin) ---
    def run_action(self, action: ActionSpec):
        df = self._guard_raptor()
        if df is None:
            return

        self.logger.log(f"Running {action.button_text}…")
        try:
            out = action.run(df)
            # store
            self._action_dfs[action.key] = out
            self.state.mark_action_computed(action.key)

            # show
            view = self.action_views[action.key]
            view.set_dataframe(out)
            self.logger.log(f"{action.name} ready: {len(out):,} rows × {out.shape[1]} cols.")
            self.show_action(action)

            self._refresh_pipeline_ui()
        except Exception as e:
            self.logger.log(f"ERROR in {action.button_text}: {e}")
            messagebox.showerror(f"{action.button_text} error", str(e))

    def run_all(self):
        """
        Run all actions in order.
        Loading underlyings/raptor is kept explicit (fast + avoids freezing UI).
        """
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
