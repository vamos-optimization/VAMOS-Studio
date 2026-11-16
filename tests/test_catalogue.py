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
            "ccmo",
            "cmoeams",
            "ctaea",
            "ibea",
            "moead",
            "nsgaii",
            "nsgaiii",
            "rvea",
            "smpso",
            "smsemoa",
            "spea2",
            "top",
        }

    def test_should_make_nsgaii_moead_and_smsemoa_available_for_real_and_binary_problems(self):
        # Act
        available = {
            entry.key: entry.encodings for entry in catalogue.algorithm_entries() if entry.available
        }

        # Assert
        assert available == {
            "nsgaii": ("real", "binary"),
            "moead": ("real", "binary"),
            "smsemoa": ("real", "binary"),
        }


class TestProblems:
    @pytest.mark.parametrize(
        ("key", "family"),
        [("zdt1", "zdt"), ("dtlz7", "dtlz"), ("cec2009_uf1", "cec2009_uf"), ("lz09_f1", "lz09_f")],
    )
    def test_should_find_the_family_of_a_problem(self, key, family):
        # Act / Assert
        assert catalogue.family_of(key) == family

    def test_should_make_the_zdt_dtlz_and_simple_binary_problems_available(self):
        # Act
        available = {entry.key for entry in catalogue.problem_entries() if entry.available}

        # Assert
        assert available == {f"zdt{number}" for number in range(1, 7)} | {
            f"dtlz{number}" for number in range(1, 8)
        } | {"bin_knapsack", "bin_qubo", "bin_feat"}

    def test_should_offer_two_to_twenty_objectives_for_dtlz_only(self):
        # Act / Assert
        assert catalogue.problem_entry("dtlz2").n_obj_options == tuple(range(2, 21))
        assert catalogue.problem_entry("zdt1").n_obj_options == (2,)

    @pytest.mark.parametrize(("n_obj", "n_var"), [(2, 11), (3, 12)])
    def test_should_derive_the_variables_of_dtlz2_from_its_objectives(self, n_obj, n_var):
        # Act
        details = catalogue.problem_details("dtlz2", n_obj)

        # Assert
        assert (details.n_var, details.n_obj, len(details.lower)) == (n_var, n_obj, n_var)
        assert details.reference_front.shape[1] == n_obj

    def test_should_refuse_a_number_of_objectives_it_does_not_offer(self):
        # Act / Assert
        with pytest.raises(ValueError):
            catalogue.problem_details("dtlz2", 21)

    def test_should_list_zdt5_as_binary_and_available(self):
        # Act
        entry = catalogue.problem_entry("zdt5")

        # Assert
        assert entry.encoding == "binary"
        assert entry.available

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
        assert catalogue.reference_front_source(key, 2) == "jMetal 7.11"

    def test_should_fall_back_to_vamos_for_other_problems(self):
        # Act / Assert
        assert catalogue.reference_front_source("wfg1", 2).startswith("VAMOS ")

    DTLZ_SURFACES = {
        "dtlz1": lambda front: front.sum(axis=1) - 0.5,
        "dtlz2": lambda front: np.linalg.norm(front, axis=1) - 1,
        "dtlz3": lambda front: np.linalg.norm(front, axis=1) - 1,
        "dtlz4": lambda front: np.linalg.norm(front, axis=1) - 1,
    }

    @pytest.mark.parametrize("n_obj", [2, 3])
    @pytest.mark.parametrize("key", sorted(DTLZ_SURFACES))
    def test_should_lie_on_the_dtlz_surfaces(self, key, n_obj):
        """DTLZ1's front is the plane sum(f) = 0.5; DTLZ2-4's, the unit sphere."""
        # Arrange
        front = catalogue.reference_front(key, n_obj)

        # Act
        deviation = np.max(np.abs(self.DTLZ_SURFACES[key](front)))

        # Assert
        assert front.shape[1] == n_obj
        assert deviation < 1e-6
        assert catalogue.reference_front_source(key, n_obj) == "jMetal 7.11"

    @pytest.mark.parametrize("n_obj", [2, 3])
    @pytest.mark.parametrize("number", range(1, 8))
    def test_should_have_a_front_for_every_dtlz_problem(self, number, n_obj):
        # Act
        front = catalogue.reference_front(f"dtlz{number}", n_obj)

        # Assert
        assert front is not None and front.shape[1] == n_obj

    def test_should_report_where_the_front_of_a_problem_comes_from(self):
        # Act
        details = catalogue.problem_details("zdt4")

        # Assert
        assert details.reference_front_source == "jMetal 7.11"
        assert details.reference_front.shape == (1000, 2)


class TestProblemArguments:
    @pytest.mark.parametrize(
        ("key", "expected"),
        [
            ("zdt1", [("n_var", "integer", 30)]),
            ("dtlz2", [("n_var", "integer", 12), ("n_obj", "integer", 3)]),
            (
                "zcat1",
                [
                    ("n_var", "integer", 30),
                    ("n_obj", "integer", 2),
                    ("complicated_pareto_set", "boolean", False),
                    ("level", "integer", 1),
                    ("bias", "boolean", False),
                    ("imbalance", "boolean", False),
                ],
            ),
        ],
    )
    def test_should_read_the_arguments_of_vamos_constructors(self, key, expected):
        # Act
        arguments = catalogue.problem_arguments(key)

        # Assert
        assert [(a.name, a.type, a.default) for a in arguments] == expected

    @pytest.mark.parametrize(
        ("key", "arguments", "valid"),
        [
            ("zdt1", {"n_var": 2}, True),
            ("zdt1", {"n_var": 1}, False),
            ("dtlz2", {"n_var": 3, "n_obj": 3}, True),
            ("dtlz2", {"n_var": 2, "n_obj": 3}, False),
            ("dtlz2", {"n_var": 14, "n_obj": 5}, True),
            ("dtlz2", {"n_var": 30, "n_obj": 21}, False),
        ],
    )
    def test_should_check_the_arguments(self, key, arguments, valid):
        # Act / Assert
        assert (catalogue.argument_problems(key, arguments) == []) is valid

    def test_should_build_a_problem_with_the_variables_set(self):
        # Act
        details = catalogue.problem_details("zdt1", n_var=8)

        # Assert
        assert details.n_var == 8 and len(details.upper) == 8

    def test_should_refuse_to_build_a_problem_with_invalid_arguments(self):
        # Act / Assert
        with pytest.raises(ValueError, match="at least 3 variables"):
            catalogue.problem_details("dtlz2", 3, 2)
