
from __future__ import annotations

import tkinter as tk
from datetime import datetime


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
