"""Tests for the Optimize and Analyze pages, through the app's navigation (Streamlit's AppTest).

A run is launched from New run as a user would, and then followed in the other pages.
"""

from pathlib import Path

import pytest
from conftest import make_request, wait_for_end, wait_until
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


class TestProblemArguments:
    def test_should_launch_a_problem_with_the_variables_set(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))
        app = open_page(NEW_RUN)
        checkbox(app, "Set its arguments").check().run()
        number_input(app, "Variables").set_value(10).run()
        number_input(app, "Evaluations").set_value(2000).run()

        # Act
        next(b for b in app.button if b.label == "Launch the run").click().run()
        run = runs.list_runs(tmp_path)[0]
        wait_for_end(run)

        # Assert
        assert runs.read_request(run).n_var == 10
        assert runs.result_front(run)[1].shape[1] == 10

    def test_should_not_launch_with_invalid_arguments(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))
        app = open_page(NEW_RUN)
        problem = next(box for box in app.selectbox if box.label == "Problem")
        problem.select_index(problem.options.index("DTLZ2")).run()
        checkbox(app, "Set its arguments").check().run()

        # Act
        number_input(app, "Variables").set_value(2).run()

        # Assert
        assert "DTLZ2 with 3 objectives needs at least 3 variables." in [e.value for e in app.error]
        assert next(b for b in app.button if b.label == "Launch the run").disabled


class TestBinaryProblem:
    def test_should_solve_knapsack_and_show_its_results_without_a_reference_front(
        self, tmp_path, monkeypatch
    ):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))
        app = open_page(NEW_RUN)
        problem = next(box for box in app.selectbox if box.label == "Problem")
        problem.select_index(problem.options.index("Binary Knapsack")).run()
        number_input(app, "Evaluations").set_value(2000).run()

        # Act
        next(b for b in app.button if b.label == "Launch the run").click().run()
        run = runs.list_runs(tmp_path)[0]
        wait_for_end(run)
        results = open_page(RESULTS)

        # Assert
        assert runs.read_request(run).encoding == "binary"
        assert not results.exception
        assert any("no reference front" in info.value for info in results.info)
        solutions = results.dataframe[-1].value
        assert set(solutions["x1"].unique()) <= {0, 1}
        assert solutions["x1"].dtype.kind == "i"


PROBLEMS = "pages/explore_problems.py"


def launch_knapsack(app: AppTest) -> runs.SolveRun:
    """Choose the binary knapsack in New run, with 3000 evaluations, and launch it."""
    problem = next(box for box in app.selectbox if box.label == "Problem")
    problem.select_index(problem.options.index("Binary Knapsack")).run()
    number_input(app, "Evaluations").set_value(3000).run()
    next(b for b in app.button if b.label == "Launch the run").click().run()


def reference_radio(app: AppTest):
    return next(radio for radio in app.radio if radio.label == "Reference front")


class TestApproximateFrontsInThePages:
    def test_should_build_a_front_from_new_run_and_offer_it_afterwards(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))
        app = open_page(NEW_RUN)
        problem = next(box for box in app.selectbox if box.label == "Problem")
        problem.select_index(problem.options.index("Binary Knapsack")).run()
        before = reference_radio(app).options
        contribute_by_default = checkbox(
            app, "Add this run's solutions to the approximate reference front of this problem"
        ).value

        # Act
        launch_knapsack(app)
        wait_for_end(runs.list_runs(tmp_path)[0])
        again = open_page(NEW_RUN)
        problem = next(box for box in again.selectbox if box.label == "Problem")
        problem.select_index(problem.options.index("Binary Knapsack")).run()

        # Assert
        assert before == ["None (no indicators)"] and contribute_by_default
        options = reference_radio(again).options
        assert len(options) == 2 and options[0].startswith("Approximate front v1")

    def test_should_measure_zdt1_with_its_exact_front_by_default(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))

        # Act
        app = open_page(NEW_RUN)

        # Assert
        assert reference_radio(app).value == "exact"
        assert not checkbox(
            app, "Add this run's solutions to the approximate reference front of this problem"
        ).value

    def test_should_add_a_run_from_results(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))
        run = runs.launch(make_request("zdt1", 3000), tmp_path)
        wait_for_end(run)
        app = open_page(RESULTS)

        # Act
        next(b for b in app.button if b.label.startswith("Add this run")).click().run()

        # Assert
        assert not app.exception
        assert runs.contributed(run) is not None

    def test_should_offer_to_measure_with_a_newer_version(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))
        first = runs.launch(
            runs.SolveRequest.from_dict(
                make_request("zdt1", 3000).to_dict() | {"contribute": True}
            ),
            tmp_path,
        )
        wait_for_end(first)
        measured = runs.launch(
            runs.SolveRequest.from_dict(
                make_request("zdt1", 3000).to_dict()
                | {"seed": 2, "reference_front": "approximate", "contribute": True}
            ),
            tmp_path,
        )
        wait_for_end(measured)
        app = open_page(RESULTS)

        # Act
        app.toggle[0].set_value(True).run()

        # Assert
        assert not app.exception
        assert any("the current approximate front v2" in c.value for c in app.caption)

    def test_should_view_and_delete_a_front_in_explore_problems(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))
        run = runs.launch(
            runs.SolveRequest.from_dict(
                make_request("zdt1", 3000).to_dict() | {"contribute": True}
            ),
            tmp_path,
        )
        wait_for_end(run)
        app = open_page(PROBLEMS)

        # Act
        shown = next(box for box in app.selectbox if box.label == "Approximate front").options
        next(b for b in app.button if b.label == "Delete this approximate front…").click().run()
        next(b for b in app.button if b.label == "Yes, delete it").click().run()

        # Assert
        assert not app.exception
        assert len(shown) == 1 and "approximate front v1" in shown[0]
        assert runs.contributed(run) is None


@pytest.fixture(scope="module")
def launched_series(tmp_path_factory):
    """A series of three runs launched from New run, finished."""
    from vamos_studio.backend import series

    parent = tmp_path_factory.mktemp("series")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv(runs.RUNS_DIRECTORY_ENV, str(parent))
        app = open_page(NEW_RUN)
        number_input(app, "Evaluations").set_value(2000).run()
        number_input(app, "Independent runs").set_value(3).run()
        next(b for b in app.button if b.label == "Launch the run").click().run()
        chosen = series.list_series(parent)[0]
        wait_until(lambda: not series.state(chosen).active)
    return parent, app, chosen


class TestSeriesInThePages:
    def test_should_launch_a_series_and_analyze_it_in_results(self, launched_series, monkeypatch):
        # Arrange
        parent, app, chosen = launched_series
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(parent))

        # Act
        monitor = open_page(MONITOR)
        history = open_page(HISTORY)
        results = open_page(RESULTS)

        # Assert
        assert chosen.count == 3
        assert app.title[0].value == "Monitor"
        assert not monitor.exception and not results.exception and not history.exception
        assert set(history.dataframe[0].value["Series"]) == {chosen.series_id}
        assert results.selectbox(key="show:" + chosen.series_id).value == "All runs (aggregate)"
        summary = results.dataframe[0].value
        assert "median" in summary.columns and len(results.dataframe[1].value) == 3

    def test_should_show_a_run_of_the_series(self, launched_series, monkeypatch):
        # Arrange
        parent, _, chosen = launched_series
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(parent))
        results = open_page(RESULTS)

        # Act
        results.selectbox(key="show:" + chosen.series_id).set_value("Run with seed 2").run()

        # Assert
        assert not results.exception
        tabs = [tab.label for tab in results.tabs]
        assert tabs == ["Front", "Indicators", "Solutions", "Details"]

    def test_should_open_the_run_remembered_by_another_page(self, launched_series, monkeypatch):
        # Arrange
        from vamos_studio import ui

        parent, _, chosen = launched_series
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(parent))
        app = AppTest.from_file(APP, default_timeout=60).run()
        app.session_state[ui.SELECTED_RUN] = chosen.run_id(3)

        # Act
        results = app.switch_page(RESULTS).run()

        # Assert
        assert not results.exception
        assert results.selectbox(key="show:" + chosen.series_id).value == "Run with seed 3"

    def test_should_open_the_best_run_from_the_aggregate(self, launched_series, monkeypatch):
        # Arrange
        parent, _, chosen = launched_series
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(parent))
        results = open_page(RESULTS)

        # Act
        next(b for b in results.button if b.label.startswith("Open the best run")).click().run()

        # Assert
        assert not results.exception
        assert results.selectbox(key="show:" + chosen.series_id).value.startswith("Run with seed")
