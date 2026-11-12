"""Tests for the approximations of a reference front used by the indicator sandbox."""

import numpy as np
import pytest

from vamos_studio.front_sample import sample_front

FRONT = np.column_stack([np.linspace(0.0, 1.0, 101), 1.0 - np.linspace(0.0, 1.0, 101)])


class TestSampleFront:
    def test_should_take_evenly_spread_points_including_the_extremes(self):
        # Act
        sample = sample_front(FRONT, 5, 0.0)

        # Assert
        assert sample[:, 0].tolist() == [0.0, 0.25, 0.5, 0.75, 1.0]

    def test_should_shift_by_a_fraction_of_each_objective_range(self):
        # Arrange
        front = FRONT * np.array([1.0, 10.0])

        # Act
        sample = sample_front(front, 2, 0.1)

        # Assert
        assert sample.tolist() == [[0.1, 11.0], [1.1, 1.0]]

    def test_should_take_at_most_every_point(self):
        # Act
        sample = sample_front(FRONT, 1000, 0.0)

        # Assert
        assert len(sample) == len(FRONT)

    @pytest.mark.parametrize(("n_points", "shift"), [(0, 0.0), (5, -0.1)])
    def test_should_reject_invalid_arguments(self, n_points, shift):
        # Act / Assert
        with pytest.raises(ValueError):
            sample_front(FRONT, n_points, shift)
