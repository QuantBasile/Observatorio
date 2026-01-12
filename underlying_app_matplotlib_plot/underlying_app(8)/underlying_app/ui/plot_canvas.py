from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


@dataclass
class Series:
    """One scatter series."""

    label: str
    x: np.ndarray
    y: np.ndarray
    color: str = "#2563eb"
    marker: str = "o"  # Supported: o, s, ^, x, +


@dataclass
class PlotData:
    """Multi-series scatter."""

    series: Sequence[Series]
    title: str = ""
    highlight: Optional[dict] = None
    # highlight dict keys: x, y, color(optional), marker(optional)


class PlotCanvas(tk.Frame):
    """Matplotlib-backed plot widget (TkAgg).

    Keeps the same public API as the previous tk.Canvas-based PlotCanvas:
      - set_data(PlotData)
      - clear()
    """

    def __init__(self, parent: tk.Misc, **kwargs):
        # Accept background/bd/relief via **kwargs
        super().__init__(parent, **kwargs)

        self._data: Optional[PlotData] = None

        self.fig = Figure(figsize=(4, 3), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(left=0.14, right=0.98, bottom=0.18, top=0.90)

        self._canvas = FigureCanvasTkAgg(self.fig, master=self)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)

        self.bind("<Configure>", lambda _e: self.redraw())
        self._draw_empty("(select a row to plot)")

    def set_data(self, data: PlotData):
        self._data = data
        self.redraw()

    def clear(self):
        self._data = None
        self._draw_empty("(select a row to plot)")

    def _draw_empty(self, msg: str):
        self.ax.clear()
        self.ax.text(0.02, 0.98, msg, transform=self.ax.transAxes,
                     va="top", ha="left", fontsize=10, color="#5c6f8f")
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self._canvas.draw_idle()

    def redraw(self):
        if self._data is None:
            self._draw_empty("(select a row to plot)")
            return

        self.ax.clear()

        any_points = False
        for s in self._data.series:
            x = np.asarray(s.x, dtype=float)
            y = np.asarray(s.y, dtype=float)
            mask = np.isfinite(x) & np.isfinite(y)
            if not np.any(mask):
                continue
            any_points = True
            self.ax.scatter(
                x[mask],
                y[mask],
                s=18,
                c=s.color,
                marker=s.marker,
                alpha=0.9,
                linewidths=0.0,
                label=s.label,
            )
            
        if not any_points:
            self._draw_empty("(no finite data)")
            return

        if self._data.title:
            self.ax.set_title(self._data.title, fontsize=11, pad=10)

        # Axis labels requested
        self.ax.set_xlabel("Strike", fontsize=10)
        self.ax.set_ylabel("Sized_GAP_Ask", fontsize=10)

        # Ticks + labels
        self.ax.tick_params(axis="both", which="major", labelsize=9, length=5)
        self.ax.locator_params(axis="x", nbins=6)
        self.ax.locator_params(axis="y", nbins=6)

        # Light grid
        self.ax.grid(True, linestyle="--", alpha=0.25)

        # Highlight point
        if self._data.highlight:
            hx = self._data.highlight.get("x")
            hy = self._data.highlight.get("y")
            if hx is not None and hy is not None and np.isfinite(hx) and np.isfinite(hy):
                hcol = self._data.highlight.get("color") or "#f59e0b"
                hmk = self._data.highlight.get("marker") or "o"
                self.ax.scatter(
                    [float(hx)],
                    [float(hy)],
                    s=90,
                    marker=hmk,
                    c=hcol,
                    edgecolors="#111827",
                    linewidths=1.8,
                    zorder=10,
                )

        if len(self._data.series) > 1:
            self.ax.legend(loc="upper right", fontsize=8, frameon=False)

        self._canvas.draw_idle()
