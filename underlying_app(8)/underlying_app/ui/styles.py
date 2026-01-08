
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def apply_futuristic_style(root: tk.Misc):
    """
    Light, futuristic / "pyqt-ish" style using only ttk/tkinter.
    """
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    bg = "#f5f7fb"
    panel = "#ffffff"
    panel2 = "#eef2fb"
    fg = "#12223a"
    muted = "#5c6f8f"
    accent = "#2563eb"   # blue
    accent2 = "#22c55e"  # green

    root.configure(bg=bg)

    style.configure("App.TFrame", background=bg)
    style.configure("Panel.TFrame", background=panel)
    style.configure("Topbar.TFrame", background=panel2)
    style.configure("Nav.TFrame", background=panel2)
    style.configure("Log.TFrame", background=panel2)

    style.configure("Title.TLabel", background=panel2, foreground=fg, font=("Segoe UI", 12, "bold"))
    style.configure("Muted.TLabel", background=panel2, foreground=muted, font=("Segoe UI", 10))

    style.configure("TLabel", background=panel, foreground=fg, font=("Segoe UI", 10))

    style.configure("Nav.TButton",
                    background=panel2,
                    foreground=fg,
                    padding=(12, 10),
                    relief="flat")
    style.map("Nav.TButton",
              background=[("active", "#dde6fb")],
              foreground=[("active", accent)])

    style.configure("Accent.TButton",
                    background=accent,
                    foreground="#ffffff",
                    padding=(12, 8))
    style.map("Accent.TButton",
              background=[("active", "#1d4ed8")],
              foreground=[("active", "#ffffff")])

    style.configure("TButton", font=("Segoe UI", 10))
    style.map("TButton",
              background=[("active", "#dde6fb")],
              foreground=[("active", fg)])

    # Combobox / Entry
    style.configure("TCombobox", padding=4)
    style.configure("TEntry", padding=4)

    # Treeview
    style.configure("Treeview",
                    background=panel,
                    fieldbackground=panel,
                    foreground=fg,
                    rowheight=26,
                    bordercolor="#d2d9ea",
                    lightcolor="#d2d9ea",
                    darkcolor="#d2d9ea")
    style.map("Treeview",
              background=[("selected", "#dbeafe")],
              foreground=[("selected", fg)])

    style.configure("Treeview.Heading",
                    background=panel2,
                    foreground=fg,
                    relief="flat",
                    font=("Segoe UI", 10, "bold"))
    style.map("Treeview.Heading",
              background=[("active", "#dde6fb")],
              foreground=[("active", accent)])
