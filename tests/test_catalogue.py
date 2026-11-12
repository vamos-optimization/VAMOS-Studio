"""Tests for the catalogue of algorithms and problems."""

import numpy as np
import pytest

from vamos_studio.backend import catalogue


class TestAlgorithms:
    def test_should_list_every_vamos_algorithm(self):
        # Act
        keys = {entry.key for entry in catalogue.algorithm_entries()}

        # Assert
        assert keys == {
            "agemoea",
            "ibea",
            "moead",
            "nsgaii",
            "nsgaiii",
            "rvea",
            "smpso",
            "smsemoa",
            "spea2",
        }

    def test_should_make_only_nsgaii_for_real_problems_available(self):
        # Act
        available = {
            entry.key: entry.encodings for entry in catalogue.algorithm_entries() if entry.available
        }

        # Assert
        assert available == {"nsgaii": ("real",)}


class TestProblems:
    @pytest.mark.parametrize(
        ("key", "family"),
        [("zdt1", "zdt"), ("dtlz7", "dtlz"), ("cec2009_uf1", "cec2009_uf"), ("lz09_f1", "lz09_f")],
    )
    def test_should_find_the_family_of_a_problem(self, key, family):
        # Act / Assert
        assert catalogue.family_of(key) == family

    def test_should_make_only_the_real_coded_zdt_problems_available(self):
        # Act
        available = {entry.key for entry in catalogue.problem_entries() if entry.available}

        # Assert
        assert available == {"zdt1", "zdt2", "zdt3", "zdt4", "zdt6"}

    def test_should_list_zdt5_as_binary_and_inactive(self):
        # Act
        entry = catalogue.problem_entry("zdt5")

        # Assert
        assert entry.encoding == "binary"
        assert not entry.available

    def test_should_give_the_bounds_and_reference_front_of_zdt4(self):
        # Act
        details = catalogue.problem_details("zdt4")

        # Assert
        assert details.entry.n_var == 10
        assert (details.lower[0], details.upper[0]) == (0.0, 1.0)
        assert (details.lower[1], details.upper[1]) == (-5.0, 5.0)
        assert details.reference_front is not None
        assert details.reference_front.shape[1] == 2

    def test_should_raise_for_an_unknown_problem(self):
        # Act / Assert
        with pytest.raises(KeyError):
            catalogue.problem_entry("no_such_problem")


class TestReferenceFronts:
    """The reference fronts the studio measures against: jMetal's copy, on the true fronts."""

    ANALYTIC = {
        "zdt1": lambda f1: 1 - np.sqrt(f1),
        "zdt2": lambda f1: 1 - f1**2,
        "zdt3": lambda f1: 1 - np.sqrt(f1) - f1 * np.sin(10 * np.pi * f1),
        "zdt4": lambda f1: 1 - np.sqrt(f1),
        "zdt6": lambda f1: 1 - f1**2,
    }

    @pytest.mark.parametrize("key", sorted(ANALYTIC))
    def test_should_lie_on_the_analytic_front(self, key):
        """Within the precision of jMetal's files; VAMOS 1.1's are off by up to 0.0146."""
        # Arrange
        front = catalogue.reference_front(key, 2)

        # Act
        deviation = np.max(np.abs(front[:, 1] - self.ANALYTIC[key](front[:, 0])))

        # Assert
        assert deviation < 1e-6

    @pytest.mark.parametrize("key", sorted(ANALYTIC))
    def test_should_come_from_jmetal_for_the_zdt_problems(self, key):
        # Act / Assert
        assert catalogue.reference_front_source(key) == "jMetal 7.11"

    def test_should_fall_back_to_vamos_for_other_problems(self):
        # Act / Assert
        assert catalogue.reference_front_source("dtlz2").startswith("VAMOS ")

    def test_should_report_where_the_front_of_a_problem_comes_from(self):
        # Act
        details = catalogue.problem_details("zdt4")

        # Assert
        assert details.reference_front_source == "jMetal 7.11"
        assert details.reference_front.shape == (1000, 2)
