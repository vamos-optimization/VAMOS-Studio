"""Tests for the estimate of what pausing for the live view adds to a run."""

import pytest

from vamos_studio.live_view import estimated_generations, pause_overhead


class TestEstimatedGenerations:
    @pytest.mark.parametrize(
        ("evaluations", "pop_size", "ratio", "expected"),
        [(25000, 100, 1.0, 249), (25000, 100, 0.5, 498), (100, 100, 1.0, 1), (5000, 100, 0, 4900)],
    )
    def test_should_divide_the_budget_after_the_initial_population(
        self, evaluations, pop_size, ratio, expected
    ):
        # Act / Assert
        assert estimated_generations(evaluations, pop_size, ratio) == expected


class TestPauseOverhead:
    def test_should_count_a_pause_at_generation_zero_and_every_multiple(self):
        # Act / Assert
        assert pause_overhead(249, 0.2, 5) == pytest.approx(50 * 0.2)

    def test_should_add_nothing_without_pauses(self):
        # Act / Assert
        assert pause_overhead(249, 0.0, 5) == 0.0
