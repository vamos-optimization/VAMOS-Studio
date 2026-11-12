"""Tests for deleting runs to the trash, restoring them and emptying the trash."""

import shutil
from pathlib import Path

import pytest
from conftest import make_request, wait_until
from streamlit.testing.v1 import AppTest

from vamos_studio.backend import runs
from vamos_studio.backend.runs import RunState

APP = str(Path(__file__).resolve().parent.parent / "app.py")
HISTORY = "pages/history.py"


@pytest.fixture
def parent(tmp_path, finished_run) -> Path:
    """A runs directory with two copies of a finished run."""
    for run_id in ("20260101-000000", "20260102-000000"):
        shutil.copytree(finished_run.directory, tmp_path / run_id)
    return tmp_path


class TestTrash:
    def test_should_move_a_run_to_the_trash_and_out_of_the_list(self, parent):
        # Arrange
        run = runs.list_runs(parent)[0]

        # Act
        runs.move_to_trash(run)

        # Assert
        assert [r.run_id for r in runs.list_runs(parent)] == ["20260101-000000"]
        assert [t.run_id for t in runs.list_trash(parent)] == [run.run_id]

    def test_should_restore_a_run_with_its_results(self, parent):
        # Arrange
        run = runs.list_runs(parent)[0]
        runs.move_to_trash(run)

        # Act
        restored = runs.restore(parent, runs.list_trash(parent)[0])

        # Assert
        assert restored == run
        assert runs.state(restored) == RunState.FINISHED
        assert runs.list_trash(parent) == []
        assert len(runs.result_front(restored)[0]) > 0

    def test_should_not_restore_over_a_run_with_the_same_identifier(self, parent, finished_run):
        # Arrange
        run = runs.list_runs(parent)[0]
        runs.move_to_trash(run)
        shutil.copytree(finished_run.directory, run.directory)

        # Act / Assert
        with pytest.raises(FileExistsError):
            runs.restore(parent, runs.list_trash(parent)[0])

    def test_should_empty_the_trash_for_good(self, parent):
        # Arrange
        for run in runs.list_runs(parent):
            runs.move_to_trash(run)

        # Act
        count = runs.empty_trash(parent)

        # Assert
        assert count == 2
        assert runs.list_trash(parent) == [] and runs.list_runs(parent) == []

    def test_should_refuse_to_delete_an_active_run(self, tmp_path):
        # Arrange
        run = runs.launch(make_request("zdt4", 5_000_000), tmp_path)
        wait_until(lambda: runs.state(run).active)

        # Act / Assert
        try:
            with pytest.raises(ValueError, match="cancel it first"):
                runs.move_to_trash(run)
        finally:
            runs.cancel(run)
            wait_until(lambda: not runs.is_alive(runs.read_pid(run)))


def open_history() -> AppTest:
    return AppTest.from_file(APP, default_timeout=60).run().switch_page(HISTORY).run()


def click(app: AppTest, label: str) -> AppTest:
    return next(b for b in app.button if b.label == label).click().run()


class TestHistoryPage:
    def test_should_delete_restore_and_empty(self, parent, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(parent))
        app = open_history()

        # Act: delete one run, after confirming
        app.multiselect[0].select("20260102-000000").run()
        click(app, "Delete 1 run(s)…")
        click(app, "Yes, move to the trash")

        # Assert
        assert not app.exception
        assert [r.run_id for r in runs.list_runs(parent)] == ["20260101-000000"]
        assert app.expander[-1].label == "Trash (1)"

        # Act: restore it
        click(app, "Restore")

        # Assert
        assert len(runs.list_runs(parent)) == 2 and runs.list_trash(parent) == []

        # Act: delete both, then empty the trash
        app.multiselect[0].select("20260101-000000").select("20260102-000000").run()
        click(app, "Delete 2 run(s)…")
        click(app, "Yes, move to the trash")
        click(app, "Empty the trash…")
        click(app, "Yes, empty the trash")

        # Assert
        assert not app.exception
        assert runs.list_runs(parent) == [] and runs.list_trash(parent) == []
        assert "There are no runs yet." in [info.value for info in app.info]

    def test_should_not_delete_without_confirmation(self, parent, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(parent))
        app = open_history()
        app.multiselect[0].select("20260102-000000").run()
        click(app, "Delete 1 run(s)…")

        # Act
        click(app, "Cancel")

        # Assert
        assert len(runs.list_runs(parent)) == 2
