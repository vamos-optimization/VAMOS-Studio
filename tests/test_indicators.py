"""Tests for the quality indicators and how the studio normalizes fronts."""

import moocore
import numpy as np
import pytest

from vamos_studio.backend import indicators
from vamos_studio.backend.catalogue import reference_front

DISTANCES = ("nhv", "igd", "igd_plus", "epsilon_additive", "avg_hausdorff")


def evolver_hypervolume(front: np.ndarray, reference: np.ndarray) -> float:
    """Evolver-Studio's hypervolume.py, written directly on moocore."""
    lower = reference.min(axis=0)
    span = reference.max(axis=0) - lower
    normalized = np.clip((front - lower) / span, 0.0, 1.0)
    return float(moocore.hypervolume(normalized, ref=np.ones(front.shape[1])))


@pytest.fixture(scope="module")
def zdt1() -> np.ndarray:
    return reference_front("zdt1", 2)


class TestCatalogue:
    def test_should_make_the_whole_front_indicators_available(self):
        # Act
        keys = [entry.key for entry in indicators.available_indicators()]

        # Assert
        assert keys == ["hv", "nhv", "igd", "igd_plus", "epsilon_additive", "avg_hausdorff"]

    def test_should_say_why_each_inactive_indicator_is_not_available(self):
        # Act
        inactive = [entry for entry in indicators.INDICATORS if not entry.available]

        # Assert
        assert inactive
        assert all(entry.note for entry in inactive)

    def test_should_maximize_only_the_hypervolumes(self):
        # Act
        maximized = {entry.key for entry in indicators.INDICATORS if entry.maximized}

        # Assert
        assert maximized == {"hv", "hv_contributions", "hv_approx", "whv_rect"}


class TestNormalize:
    def test_should_map_the_reference_front_onto_the_unit_box(self, zdt1):
        # Act
        normalized = indicators.normalize(zdt1, zdt1)

        # Assert
        assert np.allclose(normalized.min(axis=0), 0.0)
        assert np.allclose(normalized.max(axis=0), 1.0)

    def test_should_only_shift_an_objective_the_reference_front_does_not_vary_in(self):
        # Arrange
        reference = np.array([[0.0, 2.0], [1.0, 2.0]])

        # Act
        normalized = indicators.normalize(np.array([[0.5, 3.0]]), reference)

        # Assert
        assert normalized.tolist() == [[0.5, 1.0]]

    def test_should_reject_fronts_with_different_numbers_of_objectives(self, zdt1):
        # Act / Assert
        with pytest.raises(ValueError):
            indicators.normalize(np.ones((3, 3)), zdt1)


class TestCompute:
    @pytest.mark.parametrize("key", DISTANCES)
    def test_should_give_zero_for_the_reference_front_itself(self, zdt1, key):
        # Act
        value = indicators.compute(key, zdt1, zdt1)

        # Assert
        assert value == pytest.approx(0.0, abs=1e-12)

    @pytest.mark.parametrize("key", DISTANCES)
    def test_should_grow_as_the_front_moves_away(self, zdt1, key):
        # Arrange
        near, far = zdt1[::50] + 0.01, zdt1[::50] + 0.05

        # Act
        values = [indicators.compute(key, front, zdt1) for front in (near, far)]

        # Assert
        assert values[0] < values[1]

    @pytest.mark.parametrize("problem", ["zdt1", "zdt3", "zdt4"])
    def test_should_measure_the_hypervolume_as_evolver_studio(self, problem):
        # Arrange
        reference = reference_front(problem, 2)
        front = reference[::40] + 0.02

        # Act
        hv = indicators.compute("hv", front, reference)
        nhv = indicators.compute("nhv", front, reference)

        # Assert
        assert hv == pytest.approx(evolver_hypervolume(front, reference))
        assert nhv == pytest.approx(
            1 - evolver_hypervolume(front, reference) / evolver_hypervolume(reference, reference)
        )

    def test_should_give_no_hypervolume_to_a_front_beyond_the_reference_point(self, zdt1):
        # Act
        value = indicators.compute("hv", zdt1 + 5.0, zdt1)

        # Assert
        assert value == 0.0

    def test_should_refuse_an_inactive_indicator(self, zdt1):
        # Act / Assert
        with pytest.raises(KeyError):
            indicators.compute("hv_contributions", zdt1, zdt1)

    def test_should_refuse_an_empty_front(self, zdt1):
        # Act / Assert
        with pytest.raises(ValueError):
            indicators.compute("igd", np.empty((0, 2)), zdt1)

    def test_should_compute_every_available_indicator(self, zdt1):
        # Act
        values = indicators.compute_all(zdt1[::100], zdt1)

        # Assert
        assert set(values) == {entry.key for entry in indicators.available_indicators()}
