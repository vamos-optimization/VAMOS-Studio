"""Tests for the subset a run returns from an unbounded archive."""

import json

import numpy as np
import pytest
from conftest import make_request

from vamos_studio.backend import runs, subset, worker
from vamos_studio.backend.catalogue import reference_front


@pytest.fixture(scope="module")
def dtlz2() -> np.ndarray:
    return reference_front("dtlz2", 3)


class TestSelect:
    @pytest.mark.parametrize("method", sorted(subset.METHODS))
    def test_should_keep_as_many_distinct_solutions_as_asked(self, dtlz2, method):
        # Act
        kept = subset.select(method, dtlz2[::10], 50)

        # Assert
        assert len(kept) == len(set(kept.tolist())) == 50
        assert kept.tolist() == sorted(kept.tolist())

    def test_should_keep_everything_from_a_small_front(self, dtlz2):
        # Act / Assert
        assert subset.select("farthest", dtlz2[:10], 50).tolist() == list(range(10))

    def test_should_spread_farthest_points_better_than_a_random_subset(self, dtlz2):
        """The max-min distance of the selection beats that of a random subset of the same size."""

        def min_gap(points):
            gaps = np.linalg.norm(points[:, None] - points[None], axis=2)
            np.fill_diagonal(gaps, np.inf)
            return gaps.min()

        # Arrange
        random = np.random.default_rng(0).choice(len(dtlz2), 100, replace=False)

        # Act
        kept = subset.select("farthest", dtlz2, 100)

        # Assert
        assert min_gap(dtlz2[kept]) > 3 * min_gap(dtlz2[random])

    def test_should_normalize_objectives_of_different_scales(self):
        """Scaling an objective does not change what farthest-point selection keeps."""
        # Arrange
        points = np.random.default_rng(1).random((300, 3))

        # Act
        kept = subset.select("farthest", points, 20)
        scaled = subset.select("farthest", points * np.array([1.0, 1.0, 100.0]), 20)

        # Assert
        assert kept.tolist() == scaled.tolist()

    @pytest.mark.parametrize(("method", "size"), [("unknown", 10), ("farthest", 0)])
    def test_should_reject_invalid_arguments(self, dtlz2, method, size):
        # Act / Assert
        with pytest.raises(ValueError):
            subset.select(method, dtlz2, size)


class TestMethodOf:
    @pytest.mark.parametrize(
        ("values", "expected"),
        [
            ({"external_archive": "unbounded", "archive_subset_selection": "crowding"}, "crowding"),
            ({"external_archive": "unbounded", "archive_subset_selection": "none"}, None),
            ({"external_archive": "bounded", "archive_prune_policy": "crowding"}, None),
            ({"external_archive": "none"}, None),
        ],
    )
    def test_should_follow_the_configuration(self, values, expected):
        # Act / Assert
        assert subset.method_of(values) == expected


class TestRunWithAnUnboundedArchive:
    def test_should_return_a_subset_as_large_as_the_population(self, tmp_path):
        # Arrange
        request = runs.SolveRequest.from_dict(
            make_request("dtlz2", 5000, external_archive="unbounded").to_dict() | {"n_obj": 3}
        )
        runs.write_json(tmp_path / runs.REQUEST_FILE, request.to_dict())

        # Act
        worker.run(tmp_path, min_interval=0.0)

        # Assert
        run = runs.SolveRun(tmp_path)
        selection = runs.read_selection(run)
        front, variables = runs.result_front(run)
        whole, _ = runs.result_front(run, whole=True)
        assert selection.method == "farthest" and selection.size == 100
        assert selection.archive_size == len(whole) > 100
        assert front.shape == (100, 3) and variables.shape == (100, 12)

    def test_should_return_the_whole_archive_when_asked_for_none(self, tmp_path):
        # Arrange
        request = make_request(
            "zdt1", 15000, external_archive="unbounded", archive_subset_selection="none"
        )
        runs.write_json(tmp_path / runs.REQUEST_FILE, request.to_dict())

        # Act
        worker.run(tmp_path, min_interval=0.0)

        # Assert
        run = runs.SolveRun(tmp_path)
        assert runs.read_selection(run) is None
        assert not (tmp_path / runs.SELECTION_FILE).exists()
        assert len(runs.result_front(run)[0]) > 100

    def test_should_record_the_selection_as_json(self, tmp_path):
        # Arrange
        request = make_request("zdt1", 3000, external_archive="unbounded")
        runs.write_json(tmp_path / runs.REQUEST_FILE, request.to_dict())

        # Act
        worker.run(tmp_path, min_interval=0.0)

        # Assert
        stored = json.loads((tmp_path / runs.SELECTION_FILE).read_text())
        assert set(stored) == {"method", "size", "archive_size", "indices"}


class TestArchiveSizeFollowsThePopulation:
    """A bounded archive is as large as the population; from an unbounded one, as many are kept."""

    @pytest.mark.parametrize("archive", ["bounded", "unbounded"])
    def test_should_return_as_many_solutions_as_the_population(self, tmp_path, archive):
        # Arrange
        request = make_request("zdt1", 15000, pop_size=60, external_archive=archive)
        runs.write_json(tmp_path / runs.REQUEST_FILE, request.to_dict())

        # Act
        worker.run(tmp_path, min_interval=0.0)

        # Assert
        front, _ = runs.result_front(runs.SolveRun(tmp_path))
        whole, _ = runs.result_front(runs.SolveRun(tmp_path), whole=True)
        assert len(front) == 60
        assert (len(whole) == 60) if archive == "bounded" else (len(whole) > 60)
