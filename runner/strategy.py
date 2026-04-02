"""Explore/exploit strategy state machine for the experiment loop.

The loop automatically switches between two modes:
- EXPLORE: bold, diverse proposals (temperature 1.0)
- EXPLOIT: focused refinement of what's working (temperature 0.3)

State transitions:
  START -> EXPLORE
  EXPLORE -> EXPLOIT  (2+ kept in last 10)
  EXPLOIT -> EXPLORE  (8 consecutive reverts)
"""

import logging

logger = logging.getLogger(__name__)

EXPLORE_PROMPT = (
    "You are in EXPLORATION mode. The current approach may be a local maximum. "
    "Try a fundamentally different strategy. Don't make small tweaks — "
    "rethink the structure, tone, or approach entirely."
)

EXPLOIT_PROMPT = (
    "You are in REFINEMENT mode. Recent changes have been working. "
    "Make small, targeted improvements to the current version. "
    "Preserve what's working. Change one thing at a time."
)

EXPLOIT_TRIGGER = 2
EXPLOIT_WINDOW = 10
EXPLORE_TRIGGER = 8


class LoopStrategy:
    """Manages explore/exploit mode switching during a run."""

    def __init__(self, override: str = "auto"):
        self._override = override
        self._history: list[bool] = []
        self._mode = "exploit" if override == "exploit_only" else "explore"

    def record(self, kept: bool) -> None:
        self._history.append(kept)
        if self._override != "auto":
            return
        self._update_mode()

    def _update_mode(self) -> None:
        old_mode = self._mode
        if self._mode == "explore":
            recent = self._history[-EXPLOIT_WINDOW:]
            if sum(recent) >= EXPLOIT_TRIGGER:
                self._mode = "exploit"
        elif self._mode == "exploit":
            if len(self._history) >= EXPLORE_TRIGGER:
                tail = self._history[-EXPLORE_TRIGGER:]
                if not any(tail):
                    self._mode = "explore"
        if old_mode != self._mode:
            logger.info("Mode switch: %s -> %s", old_mode.upper(), self._mode.upper())

    def get_mode(self) -> str:
        return self._mode

    def get_temperature(self) -> float:
        return 1.0 if self._mode == "explore" else 0.3

    def get_prompt_addition(self) -> str:
        return EXPLORE_PROMPT if self._mode == "explore" else EXPLOIT_PROMPT
