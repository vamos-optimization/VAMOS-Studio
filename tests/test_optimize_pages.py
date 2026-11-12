"""Tests for the Optimize and Analyze pages, through the app's navigation (Streamlit's AppTest).

A run is launched from New run as a user would, and then followed in the other pages.
"""

from pathlib import Path

import pytest
from conftest import wait_for_end
from streamlit.testing.v1 import AppTest

from vamos_studio.backend import runs
from vamos_studio.backend.runs import RunState

APP = str(Path(__file__).resolve().parent.parent / "app.py")
NEW_RUN, MONITOR, HISTORY, RESULTS = (
    "pages/new_run.py",
    "pages/monitor.py",
    "pages/history.py",
    "pages/results.py",
)


def open_page(page: str) -> AppTest:
    app = AppTest.from_file(APP, default_timeout=60).run()
    return app.switch_page(page).run()


def number_input(app: AppTest, label: str):
    return next(widget for widget in app.number_input if widget.label == label)


@pytest.fixture(scope="module")
def launched(tmp_path_factory) -> tuple[Path, AppTest]:
    """A run launched from the New run page with 2000 evaluations, finished."""
    parent = tmp_path_factory.mktemp("runs")
    patch = pytest.MonkeyPatch()
    patch.setenv(runs.RUNS_DIRECTORY_ENV, str(parent))
    app = open_page(NEW_RUN)
    number_input(app, "Evaluations").set_value(2000)
    next(b for b in app.button if b.label == "Launch the run").click().run()
    wait_for_end(runs.list_runs(parent)[0])
    yield parent, app
    patch.undo()


class TestNewRun:
    def test_should_start_from_the_default_configuration(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))

        # Act
        app = open_page(NEW_RUN)

        # Assert
        assert not app.exception
        assert "This is the default configuration." in [c.value for c in app.caption]
        assert app.code[0].value.startswith("--pop_size 100 --offspring_ratio 1.0")

    def test_should_show_the_parameters_of_the_chosen_crossover(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))
        app = open_page(NEW_RUN)
        crossover = next(box for box in app.selectbox if box.label == "Crossover")

        # Act
        crossover.select("blx_alpha").run()

        # Assert
        shown = {w.help.split("`")[1] for w in app.number_input if w.help and "`" in w.help}
        assert "crossover_alpha" in shown
        assert "crossover_eta" not in shown
        assert any("`crossover` sbx → blx_alpha" in c.value for c in app.caption)

    def test_should_launch_the_run_and_open_the_monitor(self, launched):
        # Arrange
        parent, app = launched

        # Act
        found = runs.list_runs(parent)

        # Assert
        assert not app.exception
        assert len(found) == 1 and runs.state(found[0]) == RunState.FINISHED
        assert app.title[0].value == "Monitor"


class TestMonitorHistoryResults:
    def test_should_show_the_finished_run_in_the_monitor(self, launched, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(launched[0]))

        # Act
        app = open_page(MONITOR)

        # Assert
        assert not app.exception
        assert "The run has finished." in [s.value for s in app.success]

    def test_should_list_the_run_in_the_history(self, launched, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(launched[0]))

        # Act
        app = open_page(HISTORY)

        # Assert
        assert not app.exception
        table = app.dataframe[0].value
        assert table["State"].tolist() == ["finished"]
        assert table["Budget"].tolist() == [2000]

    def test_should_show_the_front_indicators_and_details_of_the_run(self, launched, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(launched[0]))

        # Act
        app = open_page(RESULTS)

        # Assert
        assert not app.exception
        assert [tab.label for tab in app.tabs] == ["Front", "Indicators", "Solutions", "Details"]
        indicators = app.dataframe[1].value
        assert indicators["Indicator"].str.startswith("HV").any()
        assert any(metric.label == "Evaluations" for metric in app.metric)

    def test_should_say_there_are_no_results_without_runs(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))

        # Act
        app = open_page(RESULTS)

        # Assert
        assert not app.exception
        assert "No run has results yet." in [info.value for info in app.info]
