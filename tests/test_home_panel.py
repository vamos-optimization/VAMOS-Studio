"""Tests for what the home page shows besides its links (vamos_studio/home_panel.py)."""

from datetime import datetime
from pathlib import Path

from vamos_studio.backend import runs
from vamos_studio.home_panel import (
    activity,
    latest_changes,
    launched_at,
    quick_start_request,
)

CHANGELOG = """# Changelog

Intro.

## 0.2.0 (unreleased)

### Added

- **Series**: independent runs
  with their union.
- A plain item without a lead.
- **Explore › Problems**: every family.

## 0.1.0

- **Old**: not shown.
"""


def _write_run(parent: Path, run_id: str, state: str | None) -> runs.SolveRun:
    directory = parent / run_id
    directory.mkdir(parents=True)
    request = quick_start_request()
    runs.write_json(directory / runs.REQUEST_FILE, request.to_dict())
    if state is not None:
        runs.write_json(directory / runs.STATUS_FILE, {"state": state})
    return runs.SolveRun(directory)


class TestLaunchedAt:
    def test_should_read_the_time_from_the_run_directory_name(self):
        # Assert
        assert launched_at("20261114-101500") == datetime(2026, 11, 14, 10, 15)
        assert launched_at("series-20261114-101500_seed_3") == datetime(2026, 11, 14, 10, 15)

    def test_should_return_none_for_a_name_without_a_time(self):
        # Assert
        assert launched_at("my-run") is None


class TestLatestChanges:
    def test_should_return_the_newest_version_and_its_bold_items(self):
        # Act
        version, items = latest_changes(CHANGELOG)

        # Assert
        assert version == "0.2.0 (unreleased)"
        assert items == [
            ("Series", "independent runs with their union."),
            ("Explore › Problems", "every family."),
        ]

    def test_should_honor_the_limit(self):
        # Assert
        assert len(latest_changes(CHANGELOG, limit=1)[1]) == 1

    def test_should_return_nothing_without_a_version(self):
        # Assert
        assert latest_changes("# Changelog\n") == ("", [])


class TestActivity:
    def test_should_be_empty_without_runs(self, tmp_path):
        # Act
        summary = activity(tmp_path)

        # Assert
        assert (summary.total, summary.finished, summary.series_count) == (0, 0, 0)
        assert summary.recent == () and summary.active is None

    def test_should_find_the_newest_run_with_results(self, tmp_path):
        # Arrange
        _write_run(tmp_path, "20261114-100000", "finished")
        _write_run(tmp_path, "20261114-110000", "stopped")
        _write_run(tmp_path, "20261114-120000", "failed")

        # Act
        summary = activity(tmp_path)

        # Assert
        assert summary.latest_result.run_id == "20261114-110000"

    def test_should_count_the_runs_by_state_and_list_the_newest_first(self, tmp_path):
        # Arrange
        _write_run(tmp_path, "20261114-100000", "finished")
        _write_run(tmp_path, "20261114-110000", "failed")
        _write_run(tmp_path, "20261114-120000", "stopped")

        # Act
        summary = activity(tmp_path, limit=2)

        # Assert
        assert summary.total == 3
        assert summary.finished == 2
        assert [recent.run.run_id for recent in summary.recent] == [
            "20261114-120000",
            "20261114-110000",
        ]
        assert summary.recent[0].algorithm == "nsgaii" and summary.recent[0].problem == "zdt1"


class TestQuickStart:
    def test_should_run_nsgaii_on_zdt1_with_its_default_configuration(self):
        # Act
        request = quick_start_request()

        # Assert
        assert (request.algorithm, request.problem) == ("nsgaii", "zdt1")
        assert request.space == "nsgaii_real"
        assert request.n_var == 30
        assert request.configuration["pop_size"] == 100
