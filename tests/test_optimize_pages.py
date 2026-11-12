"""Tests for the Optimize and Analyze pages, through the app's navigation (Streamlit's AppTest).

A run is launched from New run as a user would, and then followed in the other pages.
"""

from pathlib import Path

import pytest
from conftest import make_request, wait_for_end
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


def checkbox(app: AppTest, label: str):
    return next(widget for widget in app.checkbox if widget.label == label)


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


class TestLiveView:
    def test_should_record_the_pauses_chosen_in_new_run(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))
        app = open_page(NEW_RUN)
        number_input(app, "Evaluations").set_value(2000).run()
        checkbox(app, "Slow the run down to watch the front converge").check().run()
        number_input(app, "Every (generations)").set_value(4).run()

        # Act
        next(b for b in app.button if b.label == "Launch the run").click().run()
        run = runs.list_runs(tmp_path)[0]
        wait_for_end(run)

        # Assert
        request = runs.read_request(run)
        assert (request.pause_seconds, request.pause_every) == (0.2, 4)
        assert runs.state(run) == RunState.FINISHED
        assert runs.read_status(run).paused_seconds > 0

    def test_should_estimate_what_the_pauses_add(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))
        app = open_page(NEW_RUN)

        # Act
        checkbox(app, "Slow the run down to watch the front converge").check().run()

        # Assert
        assert any(c.value.startswith("About 249 generations") for c in app.caption)


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


class TestThreeObjectives:
    def test_should_launch_dtlz2_with_three_objectives_and_show_its_results(
        self, tmp_path, monkeypatch
    ):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))
        app = open_page(NEW_RUN)
        problem = next(box for box in app.selectbox if box.label == "Problem")
        problem.select_index(problem.options.index("DTLZ2")).run()
        number_input(app, "Evaluations").set_value(2000).run()

        # Act
        next(b for b in app.button if b.label == "Launch the run").click().run()
        run = runs.list_runs(tmp_path)[0]
        wait_for_end(run)
        results = open_page(RESULTS)

        # Assert
        assert runs.read_request(run).n_obj == 3
        assert not results.exception
        assert any("with 12 variables and 3 objectives" in c.value for c in results.caption)
        assert results.dataframe[0].value.columns[:4].tolist() == ["solution", "f1", "f2", "f3"]


class TestUnboundedArchiveResults:
    def test_should_show_the_subset_and_toggle_the_whole_archive(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))
        run = runs.launch(make_request("zdt1", 15000, external_archive="unbounded"), tmp_path)
        wait_for_end(run)
        app = open_page(RESULTS)
        subset_rows = len(app.dataframe[2].value)

        # Act
        app.toggle[0].set_value(True).run()

        # Assert
        assert not app.exception
        assert "`farthest` subset selection" in app.info[0].value
        assert subset_rows == 100
        assert len(app.dataframe[2].value) > 100

    def test_should_say_the_monitor_shows_the_result_subset(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))
        run = runs.launch(make_request("zdt1", 15000, external_archive="unbounded"), tmp_path)
        wait_for_end(run)

        # Act
        app = open_page(MONITOR)

        # Assert
        assert not app.exception
        assert any(c.value.startswith("The result: 100 of the") for c in app.caption)
