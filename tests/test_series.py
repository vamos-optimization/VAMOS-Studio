"""Tests for series of independent runs and their summary."""

import dataclasses
import time

import numpy as np
import pandas as pd
import pytest
from conftest import make_request, wait_for_end, wait_until

from vamos_studio.backend import runs, series
from vamos_studio.backend.series import SeriesState
from vamos_studio.series_summary import best_run, indicator_table, summarize

LONG_BUDGET = 5_000_000


def wait_for_series(chosen: series.Series) -> SeriesState:
    wait_until(lambda: not series.state(chosen).active)
    return series.state(chosen)


class TestValidate:
    @pytest.mark.parametrize(
        ("count", "parallel", "seed", "problem"),
        [(1, 1, 1, "two runs"), (3, 0, 1, "active at a time"), (3, 1, 2**31 - 2, "exceed")],
    )
    def test_should_reject_an_invalid_series(self, count, parallel, seed, problem):
        # Act
        found = series.validate(dataclasses.replace(make_request(), seed=seed), count, parallel)

        # Assert
        assert any(problem in item for item in found)


class TestRunningASeries:
    def test_should_run_every_seed_never_more_than_parallel_at_once(self, tmp_path):
        # Arrange
        chosen = series.launch(
            dataclasses.replace(make_request("zdt1", 4000), seed=10), 4, 2, tmp_path
        )
        peak = 0

        # Act
        while series.state(chosen).active:
            active = sum(m.state in ("running", "starting") for m in series.members(chosen))
            peak = max(peak, active)
            time.sleep(0.05)

        # Assert
        assert series.state(chosen) == SeriesState.FINISHED
        assert [m.seed for m in series.members(chosen)] == [10, 11, 12, 13]
        assert [runs.read_request(m.run).seed for m in series.members(chosen)] == [10, 11, 12, 13]
        assert peak <= 2
        assert set(series.series_of_runs(tmp_path).values()) == {chosen.series_id}

    def test_should_merge_the_fronts_of_its_runs(self, tmp_path):
        # Arrange
        chosen = series.launch(make_request("zdt1", 3000), 3, 3, tmp_path)
        wait_for_series(chosen)

        # Act
        fronts = [front for _, front in series.member_fronts(chosen)]
        union = series.aggregate_front(fronts)

        # Assert
        assert len(fronts) == 3
        assert len(union) <= sum(len(front) for front in fronts)
        dominated = [
            any(np.all(other <= point) and np.any(other < point) for other in union)
            for point in union
        ]
        assert not any(dominated)

    def test_should_stop_keeping_the_results_and_launch_no_more(self, tmp_path):
        # Arrange
        chosen = series.launch(make_request("zdt4", LONG_BUDGET), 3, 1, tmp_path)
        wait_until(lambda: series.members(chosen)[0].state == "running")

        # Act
        series.stop(chosen)
        state = wait_for_series(chosen)

        # Assert
        assert state == SeriesState.STOPPED_BY_USER
        assert [m.state for m in series.members(chosen)] == [
            "stopped",
            "not started",
            "not started",
        ]

    def test_should_cancel_its_runs(self, tmp_path):
        # Arrange
        chosen = series.launch(make_request("zdt4", LONG_BUDGET), 2, 2, tmp_path)
        wait_until(lambda: all(m.state == "running" for m in series.members(chosen)))

        # Act
        series.cancel(chosen)
        state = wait_for_series(chosen)

        # Assert
        assert state == SeriesState.CANCELLED
        assert {m.state for m in series.members(chosen)} == {"cancelled"}

    def test_should_measure_every_run_against_the_same_approximate_front(self, tmp_path):
        # Arrange
        seeding = runs.launch(
            dataclasses.replace(make_request("zdt1", 3000), contribute=True), tmp_path
        )
        wait_for_end(seeding)
        request = dataclasses.replace(
            make_request("zdt1", 3000), seed=5, reference_front="approximate", contribute=True
        )

        # Act
        chosen = series.launch(request, 3, 1, tmp_path)
        wait_for_series(chosen)

        # Assert
        labels = {runs.reference_front_of(m.run)[1] for m in series.members(chosen)}
        assert len(labels) == 1 and "approximate front v1" in labels.pop()
        assert runs.contributed(seeding).version == 4

    def test_should_move_its_runs_to_the_trash(self, tmp_path):
        # Arrange
        chosen = series.launch(make_request("zdt1", 2000), 2, 2, tmp_path)
        wait_for_series(chosen)

        # Act
        moved = series.move_to_trash(chosen)

        # Assert
        assert moved == 2 and runs.list_runs(tmp_path) == []
        assert series.list_series(tmp_path) == []


class TestSummary:
    TABLE = indicator_table(
        [
            (1, "a", {"hv": 0.5, "igd": 0.3}),
            (2, "b", {"hv": 0.7, "igd": 0.1}),
            (3, "c", {"hv": 0.6, "igd": 0.2}),
        ]
    )

    def test_should_summarize_each_indicator(self):
        # Act
        summary = summarize(self.TABLE, ["hv", "igd"]).set_index("Indicator")

        # Assert
        assert summary.loc["hv", "median"] == pytest.approx(0.6)
        assert summary.loc["igd", "min"] == pytest.approx(0.1)
        assert summary.loc["hv", "IQR"] == pytest.approx(0.1)

    @pytest.mark.parametrize(
        ("indicator", "maximized", "run"), [("hv", True, "b"), ("igd", False, "b")]
    )
    def test_should_find_the_best_run(self, indicator, maximized, run):
        # Act / Assert
        assert best_run(self.TABLE, indicator, maximized) == run

    def test_should_have_one_row_per_run(self):
        # Assert
        assert isinstance(self.TABLE, pd.DataFrame)
        assert self.TABLE.columns.tolist() == ["Seed", "Run", "hv", "igd"]


class TestRunsAndSeries:
    def test_should_list_a_series_once_in_the_place_of_its_first_run(self, tmp_path):
        # Arrange
        from vamos_studio import ui

        chosen = series.Series(tmp_path / "series" / "s1", make_request(), 3, 1)
        single = runs.SolveRun(tmp_path / "single")
        other = series.Series(tmp_path / "series" / "s2", make_request(), 2, 1)
        candidates = [single, chosen.run(3), chosen.run(1), runs.SolveRun(tmp_path / "older")]

        # Act
        entries = ui.runs_and_series(candidates, [chosen, other])

        # Assert
        assert entries == [single, chosen, runs.SolveRun(tmp_path / "older")]
