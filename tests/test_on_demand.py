"""Tests for the quality indicators computed on request."""

import numpy as np
import pytest

from vamos_studio.backend.catalogue import reference_front
from vamos_studio.backend.indicators import APPROXIMATE, EXACT, compute_all
from vamos_studio.on_demand import SLOW_FROM, default_method, method_note, slow_warning


class TestSlowWarning:
    def test_should_not_warn_with_few_objectives(self):
        # Act / Assert
        assert slow_warning(SLOW_FROM - 1) is None

    def test_should_warn_with_many_objectives(self):
        # Act
        warning = slow_warning(8)

        # Assert
        assert warning is not None and "With 8 objectives the exact hypervolume" in warning


class TestHypervolumeMethod:
    @pytest.mark.parametrize(("n_obj", "expected"), [(2, EXACT), (4, EXACT), (5, APPROXIMATE)])
    def test_should_offer_the_approximation_first_with_many_objectives(self, n_obj, expected):
        # Act / Assert
        assert default_method(n_obj) == expected

    def test_should_say_when_the_hypervolume_is_approximate(self):
        # Act / Assert
        assert method_note(EXACT) is None
        assert "approximate" in method_note(APPROXIMATE)

    def test_should_approximate_the_exact_hypervolume_closely(self):
        # Arrange
        front = reference_front("dtlz2", 4)
        approximation = front[:: max(1, len(front) // 100)] * 1.05

        # Act
        exact = compute_all(approximation, front, EXACT)
        approximate = compute_all(approximation, front, APPROXIMATE)

        # Assert
        assert np.isclose(approximate["hv"], exact["hv"], rtol=1e-2)
        assert approximate["igd_plus"] == exact["igd_plus"]
