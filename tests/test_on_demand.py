"""Tests for the quality indicators computed on request."""

from vamos_studio.on_demand import SLOW_FROM, slow_warning


class TestSlowWarning:
    def test_should_not_warn_with_few_objectives(self):
        # Act / Assert
        assert slow_warning(SLOW_FROM - 1) is None

    def test_should_warn_with_many_objectives(self):
        # Act
        warning = slow_warning(8)

        # Assert
        assert warning is not None and "With 8 objectives the hypervolume" in warning
