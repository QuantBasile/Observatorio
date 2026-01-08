
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class PipelineState:
    """
    Central place to track:
      - whether datasets are loaded
      - when datasets/actions were computed
      - stale detection (e.g. action computed on old raptor)
    """
    underlyings_loaded_at: Optional[datetime] = None
    raptor_loaded_at: Optional[datetime] = None
    actions_computed_at: Dict[str, datetime] = field(default_factory=dict)

    def is_underlyings_loaded(self) -> bool:
        return self.underlyings_loaded_at is not None

    def is_raptor_loaded(self) -> bool:
        return self.raptor_loaded_at is not None

    def mark_underlyings_loaded(self):
        self.underlyings_loaded_at = datetime.now()

    def mark_raptor_loaded(self):
        self.raptor_loaded_at = datetime.now()

    def mark_action_computed(self, action_key: str):
        self.actions_computed_at[action_key] = datetime.now()

    def is_action_ready(self, action_key: str) -> bool:
        return action_key in self.actions_computed_at

    def is_action_stale(self, action_key: str) -> bool:
        """
        Action is stale if:
          - raptor exists
          - action computed
          - raptor was loaded after action computed
        """
        if self.raptor_loaded_at is None:
            return False
        t = self.actions_computed_at.get(action_key)
        if t is None:
            return False
        return self.raptor_loaded_at > t
