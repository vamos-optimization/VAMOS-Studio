"""Tests for the worker: its progress callback, and a run in the test's own process."""

import json
import time

import numpy as np
import vamos
from conftest import make_request

from vamos_studio.backend import runs, worker


def status_of(directory) -> dict:
    return json.loads((directory / runs.STATUS_FILE).read_text())


class TestFileProgress:
    def test_should_report_the_generation_evaluations_and_front(self, tmp_path):
        # Arrange
        progress = worker.FileProgress(tmp_path, max_evaluations=1000, min_interval=0.0)
        front = np.array([[0.0, 1.0], [1.0, 0.0]])

        # Act
        progress.on_start()
        progress.on_generation(3, F=front, stats={"evals": 400})

        # Assert
        assert status_of(tmp_path) | {"elapsed_seconds": 0} == {
            "state": "running",
            "generation": 3,
            "evaluations": 400,
            "max_evaluations": 1000,
            "elapsed_seconds": 0,
            "paused_seconds": 0.0,
            "ended_by": None,
            "live_source": "population",
            "error": None,
        }
        assert np.array_equal(runs.live_front(runs.SolveRun(tmp_path)), front)

    def test_should_not_rewrite_the_files_more_often_than_asked(self, tmp_path):
        # Arrange
        progress = worker.FileProgress(tmp_path, max_evaluations=1000, min_interval=3600.0)
        progress.on_start()

        # Act
        progress.on_generation(1, F=np.ones((1, 2)), stats={"evals": 200})

        # Assert
        assert status_of(tmp_path)["generation"] == 0
        assert not (tmp_path / runs.LIVE_FRONT_FILE).exists()

    def test_should_ask_vamos_to_stop_once_the_stop_mark_exists(self, tmp_path):
        # Arrange
        progress = worker.FileProgress(tmp_path, max_evaluations=1000, min_interval=0.0)
        before = progress.should_stop()

        # Act
        (tmp_path / runs.STOP_FILE).write_text("stop")

        # Assert
        assert before is False
        assert progress.should_stop() is True
        assert progress.stopped


class TestPauses:
    def test_should_report_the_front_and_pause_at_every_chosen_generation(self, tmp_path):
        # Arrange
        progress = worker.FileProgress(
            tmp_path, 1000, min_interval=3600.0, pause_seconds=0.1, pause_every=5
        )
        progress.on_start()

        # Act
        started = time.monotonic()
        progress.on_generation(5, F=np.ones((1, 2)), stats={"evals": 600})
        took = time.monotonic() - started

        # Assert
        assert took >= 0.1
        assert progress.paused_seconds >= 0.1
        assert status_of(tmp_path)["generation"] == 5
        assert (tmp_path / runs.LIVE_FRONT_FILE).exists()

    def test_should_not_pause_between_the_chosen_generations(self, tmp_path):
        # Arrange
        progress = worker.FileProgress(
            tmp_path, 1000, min_interval=3600.0, pause_seconds=5.0, pause_every=5
        )
        progress.on_start()

        # Act
        started = time.monotonic()
        progress.on_generation(3, F=np.ones((1, 2)), stats={"evals": 400})

        # Assert
        assert time.monotonic() - started < 0.5
        assert progress.paused_seconds == 0.0

    def test_should_end_a_pause_early_when_a_stop_is_requested(self, tmp_path):
        # Arrange
        progress = worker.FileProgress(tmp_path, 1000, min_interval=0.0, pause_seconds=30.0)
        (tmp_path / runs.STOP_FILE).write_text("stop")

        # Act
        started = time.monotonic()
        progress.on_generation(0, F=np.ones((1, 2)), stats={"evals": 200})

        # Assert
        assert time.monotonic() - started < 1.0
        assert progress.stopped

    def test_should_not_change_the_results(self, tmp_path):
        """Sleeping uses no random numbers: same seed, same front, with or without pauses."""
        # Arrange
        fronts = []
        for name, pause in (("plain", 0.0), ("paused", 0.01)):
            directory = tmp_path / name
            directory.mkdir()
            request = make_request(max_evaluations=1500).to_dict() | {
                "pause_seconds": pause,
                "pause_every": 2,
            }
            runs.write_json(directory / runs.REQUEST_FILE, request)

            # Act
            assert worker.run(directory, min_interval=0.0) == 0
            fronts.append(vamos.load_result(directory / runs.ARTIFACT_DIRECTORY).front())

        # Assert
        assert np.array_equal(fronts[0], fronts[1])
        assert status_of(tmp_path / "paused")["paused_seconds"] > 0


class TestRun:
    def test_should_run_a_request_and_save_its_artifact(self, tmp_path):
        # Arrange
        runs.write_json(tmp_path / runs.REQUEST_FILE, make_request(max_evaluations=1000).to_dict())

        # Act
        code = worker.run(tmp_path, min_interval=0.0)

        # Assert
        assert code == 0
        assert status_of(tmp_path)["state"] == "finished"
        assert status_of(tmp_path)["ended_by"] == "evaluations"
        assert (tmp_path / runs.ARTIFACT_DIRECTORY / "manifest.json").is_file()

    def test_should_fail_without_a_request(self, tmp_path):
        # Act
        code = worker.run(tmp_path)

        # Assert
        assert code == 1
        assert status_of(tmp_path)["state"] == "failed"

    def test_should_refuse_a_wrong_number_of_arguments(self):
        # Act / Assert
        assert worker.main([]) == 2
