"""How much pausing for the live view adds to a run, so New run can say it before launching.

Pure arithmetic, no Streamlit.
"""

from __future__ import annotations

import math


def estimated_generations(max_evaluations: int, pop_size: int, offspring_ratio: float) -> int:
    """About how many generations a generational algorithm runs within the budget.

    The initial population takes `pop_size` evaluations and each generation evaluates its
    offspring, `pop_size * offspring_ratio` (at least one).
    """
    offspring = max(1, round(pop_size * offspring_ratio))
    return max(1, math.ceil(max(0, max_evaluations - pop_size) / offspring))


def pause_overhead(generations: int, pause_seconds: float, pause_every: int) -> float:
    """The seconds the pauses add to a run of `generations` generations.

    The worker pauses at every generation that is a multiple of `pause_every`, starting at 0.
    """
    if pause_seconds <= 0:
        return 0.0
    return (generations // max(1, pause_every) + 1) * pause_seconds
