"""Tests for approximate reference fronts, alone and through runs."""

import dataclasses
import threading
import time

import numpy as np
import pytest
from conftest import make_request, wait_for_end

from vamos_studio.backend import approximate_fronts as af
from vamos_studio.backend import runs
from vamos_studio.backend.upstream.vamos_bridge import builtin_space

ARGUMENTS = {"n_var": 50, "capacity_ratio": 0.4, "n_obj": 2}


def add(parent, points, run_id, arguments=ARGUMENTS):
    return af.add(
        parent, "bin_knapsack", arguments, np.asarray(points, float),
        run_id=run_id, algorithm="nsgaii", evaluations=1000,
    )  # fmt: skip


class TestKeys:
    def test_should_fill_in_the_defaults_of_the_problem(self):
        # Act
        arguments = af.front_arguments("bin_knapsack", 50, 2)

        # Assert
        assert arguments == ARGUMENTS

    def test_should_keep_a_front_per_set_of_arguments(self, tmp_path):
        # Act
        same = af.front_directory(tmp_path, "bin_knapsack", dict(reversed(ARGUMENTS.items())))
        other = af.front_directory(tmp_path, "bin_knapsack", ARGUMENTS | {"n_var": 100})

        # Assert
        assert same == af.front_directory(tmp_path, "bin_knapsack", ARGUMENTS)
        assert other != same


class TestMerge:
    def test_should_keep_the_non_dominated_points_once(self):
        # Act
        merged = af.merge(
            np.array([[1.0, 3.0], [2.0, 2.0]]), np.array([[2.0, 2.0], [1.5, 2.5], [3.0, 3.0]])
        )

        # Assert
        assert sorted(map(tuple, merged)) == [(1.0, 3.0), (1.5, 2.5), (2.0, 2.0)]

    def test_should_cap_the_size_keeping_the_extremes(self):
        # Arrange
        f1 = np.linspace(0.0, 1.0, 500)
        front = np.column_stack([f1, 1.0 - f1])

        # Act
        merged = af.merge(None, front, cap=50)

        # Assert
        assert len(merged) == 50
        assert {0.0, 1.0} <= set(merged[:, 0].round(6))


class TestAdd:
    def test_should_create_a_front_and_grow_its_version(self, tmp_path):
        # Act
        first = add(tmp_path, [[1.0, 3.0], [3.0, 1.0]], "run-1")
        second = add(tmp_path, [[2.0, 2.0], [4.0, 4.0]], "run-2")

        # Assert
        assert (first.version, len(first.points)) == (1, 2)
        assert (second.version, len(second.points)) == (2, 3)
        assert [c.run_id for c in second.contributions] == ["run-1", "run-2"]
        assert second.contributions[1].points == 2

    def test_should_add_a_run_only_once(self, tmp_path):
        # Arrange
        add(tmp_path, [[1.0, 3.0]], "run-1")

        # Act
        again = add(tmp_path, [[0.0, 0.0]], "run-1")

        # Assert
        assert again.version == 1 and again.points.tolist() == [[1.0, 3.0]]

    def test_should_not_lose_a_run_when_two_end_at_once(self, tmp_path):
        # Arrange
        threads = [
            threading.Thread(target=add, args=(tmp_path, [[i, 10.0 - i]], f"run-{i}"))
            for i in range(8)
        ]

        # Act
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Assert
        front = af.load(tmp_path, "bin_knapsack", ARGUMENTS)
        assert front.version == 8 and len(front.contributions) == 8 and len(front.points) == 8

    def test_should_take_over_a_lock_left_by_a_dead_process(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setattr(af, "LOCK_TIMEOUT_SECONDS", 0.2)
        directory = af.front_directory(tmp_path, "bin_knapsack", ARGUMENTS)
        directory.mkdir(parents=True)
        (directory / af.LOCK_FILE).write_text("")
        time.sleep(0.5)

        # Act
        front = add(tmp_path, [[1.0, 1.0]], "run-1")

        # Assert
        assert front.version == 1

    def test_should_list_and_delete_fronts(self, tmp_path):
        # Arrange
        add(tmp_path, [[1.0, 1.0]], "run-1")
        add(tmp_path, [[1.0, 1.0]], "run-2", ARGUMENTS | {"n_var": 100})

        # Act
        listed = af.list_fronts(tmp_path, "bin_knapsack")
        af.delete(listed[0])

        # Assert
        assert len(listed) == 2
        assert len(af.list_fronts(tmp_path)) == 1


@pytest.fixture
def knapsack_request():
    binary = builtin_space("nsgaii", "binary")
    return dataclasses.replace(
        make_request(max_evaluations=3000),
        problem="bin_knapsack",
        encoding="binary",
        space=binary.name,
        space_hash=binary.content_hash(),
        configuration=dict(binary.default_configuration().values),
        n_var=50,
    )


class TestThroughRuns:
    def test_should_add_a_run_that_asks_for_it_when_it_ends(self, tmp_path, knapsack_request):
        # Act
        run = runs.launch(
            dataclasses.replace(knapsack_request, reference_front="none", contribute=True), tmp_path
        )
        wait_for_end(run)

        # Assert
        front = runs.contributed(run)
        whole, _ = runs.result_front(run, whole=True)
        assert front is not None and front.version == 1
        assert front.contributions[0].points == len(whole)

    def test_should_measure_a_run_against_a_copy_of_the_front_at_launch(
        self, tmp_path, knapsack_request
    ):
        # Arrange
        first = runs.launch(
            dataclasses.replace(knapsack_request, reference_front="none", contribute=True), tmp_path
        )
        wait_for_end(first)

        # Act
        measured = runs.launch(
            dataclasses.replace(
                knapsack_request, seed=2, reference_front="approximate", contribute=True
            ),
            tmp_path,
        )
        wait_for_end(measured)

        # Assert
        points, label = runs.reference_front_of(measured)
        assert "approximate front v1" in label
        assert runs.contributed(measured).version == 2
        version_1 = af.merge(None, runs.result_front(first, whole=True)[0])
        assert np.allclose(np.sort(points, axis=0), np.sort(version_1, axis=0))

    def test_should_refuse_to_measure_against_a_front_that_does_not_exist(
        self, tmp_path, knapsack_request
    ):
        # Act / Assert
        with pytest.raises(ValueError, match="no approximate front"):
            runs.launch(
                dataclasses.replace(knapsack_request, reference_front="approximate"), tmp_path
            )

    def test_should_add_a_finished_run_later(self, tmp_path, knapsack_request):
        # Arrange
        run = runs.launch(dataclasses.replace(knapsack_request, reference_front="none"), tmp_path)
        wait_for_end(run)
        before = runs.contributed(run)

        # Act
        front = runs.contribute(run)

        # Assert
        assert before is None
        assert front.version == 1
        assert [c.run_id for c in runs.contributed(run).contributions] == [run.run_id]

    def test_should_measure_old_runs_against_the_exact_front(self, finished_run):
        # Act
        points, label = runs.reference_front_of(finished_run)

        # Assert
        assert points is not None and label == "the exact front (jMetal 7.11)"
