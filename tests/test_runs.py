"""Tests for solve runs: launching the worker, following, stopping and cancelling runs."""

import os
import signal
from datetime import datetime

import pytest
import vamos
from conftest import make_request, wait_for_end, wait_until

from vamos_studio.backend import runs
from vamos_studio.backend.runs import RunState

LONG_BUDGET = 5_000_000


class TestRequest:
    def test_should_survive_a_round_trip_through_a_mapping(self):
        # Arrange
        request = make_request(crossover="blx_alpha", crossover_alpha=0.3)

        # Act
        restored = runs.SolveRequest.from_dict(request.to_dict())

        # Assert
        assert restored == request

    def test_should_read_a_request_stored_before_the_live_view_options(self):
        # Arrange
        stored = make_request().to_dict()
        del stored["pause_seconds"], stored["pause_every"]

        # Act
        request = runs.SolveRequest.from_dict(stored)

        # Assert
        assert (request.pause_seconds, request.pause_every) == (0.0, 1)

    def test_should_name_a_new_directory_after_the_time_without_reusing_one(self, tmp_path):
        # Arrange
        now = datetime(2026, 11, 12, 15, 30, 0)
        (tmp_path / "20261112-153000").mkdir()

        # Act
        directory = runs.new_run_directory(tmp_path, now)

        # Assert
        assert directory.name == "20261112-153000-2"


class TestFinishedRun:
    def test_should_finish_with_the_whole_budget(self, finished_run):
        # Act
        status = runs.read_status(finished_run)

        # Assert
        assert runs.state(finished_run) == RunState.FINISHED
        assert status.evaluations == status.max_evaluations == 2000
        assert status.fraction_done == 1.0

    def test_should_keep_a_vamos_run_artifact_that_verifies(self, finished_run):
        # Act
        verification = runs.verify(finished_run)

        # Assert
        assert verification.status == "succeeded"
        assert verification.integrity == "valid"

    def test_should_give_the_non_dominated_front_and_its_variables(self, finished_run):
        # Act
        front, variables = runs.result_front(finished_run)

        # Assert
        assert front.shape[1] == 2
        assert variables.shape == (len(front), 30)
        result = vamos.load_result(finished_run.artifact)
        assert len(front) == len(result.front())

    def test_should_leave_the_last_live_front(self, finished_run):
        # Act
        front = runs.live_front(finished_run)

        # Assert
        assert front is not None and front.shape[1] == 2

    def test_should_record_what_vamos_ran(self, finished_run):
        # Act
        manifest = runs.manifest(finished_run)

        # Assert
        assert manifest["outcome"]["evaluations"] == 2000
        assert manifest["resolved_spec"]["seed"] == 1


class TestStopAndCancel:
    def test_should_stop_a_run_keeping_its_results(self, tmp_path):
        # Arrange
        run = runs.launch(make_request("zdt4", LONG_BUDGET), tmp_path)
        wait_until(lambda: (runs.read_status(run) or runs.RunStatus("x")).evaluations > 5000)

        # Act
        runs.request_stop(run)
        state = wait_for_end(run)

        # Assert
        assert state == RunState.STOPPED
        assert runs.read_status(run).evaluations < LONG_BUDGET
        assert runs.read_status(run).ended_by == "user"
        assert len(runs.result_front(run)[0]) > 0

    def test_should_cancel_a_run_without_results(self, tmp_path):
        # Arrange
        run = runs.launch(make_request("zdt4", LONG_BUDGET), tmp_path)
        wait_until(lambda: runs.state(run) == RunState.RUNNING)

        # Act
        runs.cancel(run)
        wait_until(lambda: not runs.is_alive(runs.read_pid(run)))

        # Assert
        assert runs.state(run) == RunState.CANCELLED
        with pytest.raises(FileNotFoundError):
            runs.result_front(run)

    def test_should_find_the_active_run_only_while_it_is_active(self, tmp_path):
        # Arrange
        run = runs.launch(make_request("zdt4", LONG_BUDGET), tmp_path)

        # Act
        active = runs.find_active_run(tmp_path)
        runs.cancel(run)
        wait_until(lambda: not runs.is_alive(runs.read_pid(run)))

        # Assert
        assert active == run
        assert runs.find_active_run(tmp_path) is None


class TestProblems:
    def test_should_report_a_failure_and_its_reason(self, tmp_path):
        # Arrange
        request = runs.SolveRequest.from_dict(
            make_request().to_dict() | {"space_hash": "sha256:other"}
        )

        # Act
        state = wait_for_end(runs.launch(request, tmp_path))
        run = runs.list_runs(tmp_path)[0]

        # Assert
        assert state == RunState.FAILED
        assert "changed since the run was requested" in runs.read_status(run).error
        assert "Traceback" in runs.log_tail(run)

    def test_should_call_a_run_whose_worker_died_interrupted(self, tmp_path):
        # Arrange
        run = runs.launch(make_request("zdt4", LONG_BUDGET), tmp_path)
        wait_until(lambda: runs.state(run) == RunState.RUNNING)

        # Act
        os.kill(runs.read_pid(run), signal.SIGKILL)
        wait_until(lambda: not runs.is_alive(runs.read_pid(run)))

        # Assert
        assert runs.state(run) == RunState.INTERRUPTED

    def test_should_list_runs_newest_first(self, tmp_path):
        # Arrange
        for name in ("20260101-000000", "20260301-000000", "20260201-000000"):
            (tmp_path / name).mkdir()
            (tmp_path / name / runs.REQUEST_FILE).write_text("{}")
        (tmp_path / "not-a-run").mkdir()

        # Act
        listed = [run.run_id for run in runs.list_runs(tmp_path)]

        # Assert
        assert listed == ["20260301-000000", "20260201-000000", "20260101-000000"]
