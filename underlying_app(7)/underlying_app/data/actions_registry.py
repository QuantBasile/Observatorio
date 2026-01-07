
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import pandas as pd


@dataclass(frozen=True)
class ActionSpec:
    """
    Plugin-like definition for an action that consumes a base dataframe (typically Raptor)
    and returns a result dataframe for display.
    """
    key: str                 # e.g. "action1"
    name: str                # label, e.g. "Acción 1"
    button_text: str         # top bar button text, e.g. "Calculate 1"
    view_title: str          # view title
    run: Callable[[pd.DataFrame], pd.DataFrame]
    enable_filters: bool = False
    row_limit: Optional[int] = 2000


def get_default_actions() -> list[ActionSpec]:
    # Imported lazily to avoid circular imports
    from .actions import action_1, action_2, action_3

    return [
        ActionSpec(key="action1", name="Acción 1", button_text="Calculate 1", view_title="Acción 1", run=action_1),
        ActionSpec(key="action2", name="Acción 2", button_text="Calculate 2", view_title="Acción 2", run=action_2),
        ActionSpec(key="action3", name="Acción 3", button_text="Calculate 3", view_title="Acción 3", run=action_3),
    ]
