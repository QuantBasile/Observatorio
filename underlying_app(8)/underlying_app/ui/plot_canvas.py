
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class PlotData:
    x: np.ndarray
    y: np.ndarray
    highlight: Optional[tuple[float, float]] = None
    title: str = ""


class PlotCanvas(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, highlightthickness=1, highlightbackground="#d2d9ea", bg="#ffffff", **kwargs)
        self._data: Optional[PlotData] = None
        self._max_points = 2000
        self.bind("<Configure>", lambda e: self.redraw())

    def set_data(self, data: PlotData):
        self._data = data
        self.redraw()

    def clear(self):
        self._data = None
        self.delete("all")

    def redraw(self):
        self.delete("all")
        if self._data is None:
            self.create_text(10, 10, anchor="nw", text="(select a row to plot)", fill="#5c6f8f")
            return

        x = np.asarray(self._data.x)
        y = np.asarray(self._data.y)
        if x.size == 0 or y.size == 0:
            self.create_text(10, 10, anchor="nw", text="(no data)", fill="#5c6f8f")
            return

        w = max(10, int(self.winfo_width()))
        h = max(10, int(self.winfo_height()))
        pad = 40

        # Downsample (stride)
        n = int(min(len(x), len(y)))
        if n > self._max_points:
            step = max(1, n // self._max_points)
            x = x[:n:step]
            y = y[:n:step]
        else:
            x = x[:n]
            y = y[:n]

        x = x.astype(float, copy=False)
        y = y.astype(float, copy=False)

        mask = np.isfinite(x) & np.isfinite(y)
        x = x[mask]
        y = y[mask]

        if x.size == 0:
            self.create_text(10, 10, anchor="nw", text="(no finite data)", fill="#5c6f8f")
            return

        xmin, xmax = float(np.min(x)), float(np.max(x))
        ymin, ymax = float(np.min(y)), float(np.max(y))
        if xmin == xmax:
            xmax = xmin + 1.0
        if ymin == ymax:
            ymax = ymin + 1.0

        # Axes
        self.create_line(pad, h - pad, w - pad, h - pad, fill="#c7d2fe")
        self.create_line(pad, h - pad, pad, pad, fill="#c7d2fe")

        if self._data.title:
            self.create_text(pad, 10, anchor="nw", text=self._data.title, fill="#12223a")

        def sx(v): return pad + (v - xmin) / (xmax - xmin) * (w - 2 * pad)
        def sy(v): return (h - pad) - (v - ymin) / (ymax - ymin) * (h - 2 * pad)

        r = 2
        for xv, yv in zip(x, y):
            cx, cy = sx(float(xv)), sy(float(yv))
            self.create_oval(cx - r, cy - r, cx + r, cy + r, outline="", fill="#2563eb")

        if self._data.highlight is not None:
            hx, hy = self._data.highlight
            try:
                cx, cy = sx(float(hx)), sy(float(hy))
                R = 7
                self.create_oval(cx - R, cy - R, cx + R, cy + R, outline="#ef4444", width=2, fill="")
            except Exception:
                pass
