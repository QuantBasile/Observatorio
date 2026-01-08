
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Any

import pandas as pd


@dataclass(frozen=True)
class ActionSpec:
    key: str
    name: str
    button_text: str
    view_title: str
    run: Callable[[pd.DataFrame], Any]
    view_type: str = "table"     # "table", "spread_matrix", "table_plot"
    enable_filters: bool = False
    row_limit: Optional[int] = 2000


def get_default_actions() -> list[ActionSpec]:
    from .actions import action_1, action_2, action_3, action_4, action_5, action_issuer_plot_table, action_7

    return [
        ActionSpec("action1", "Acción 1", "Calculate 1", "Acción 1", action_1, "table"),
        ActionSpec("action2", "Acción 2", "Calculate 2", "Acción 2", action_2, "table"),
        ActionSpec("action3", "Acción 3", "Calculate 3", "Acción 3", action_3, "table"),
        ActionSpec("action4", "Acción 4", "Calculate 4", "Acción 4", action_4, "table"),
        ActionSpec("action5", "Acción 5", "Calculate 5", "Acción 5", action_5, "table"),
        ActionSpec("action6", "Spread Matrix", "Matrix", "Spread Matrix", lambda df: df, "spread_matrix"),
        ActionSpec("action7", "Issuer Plot", "Plot", "Issuer Plot", action_issuer_plot_table, "table_plot"),
    ]
