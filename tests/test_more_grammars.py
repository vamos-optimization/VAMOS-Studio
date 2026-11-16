"""Tests for the MOEA/D, SMS-EMOA, AGE-MOEA, RVEA and SPEA2 grammars against VAMOS.

As for NSGA-II: their real-coded defaults run exactly as VAMOS's own defaults (rule G7), and
they describe the parameters of VAMOS's tuning spaces, once the studio's changes are undone.
"""

import dataclasses

import numpy as np
import pytest
import vamos
from conftest import make_request, wait_for_end
from vamos.algorithms import AGEMOEAConfig, MOEADConfig, RVEAConfig, SMSEMOAConfig, SPEA2Config
from vamos.engine.tuning.racing import bridge_spaces
from vamos.engine.tuning.racing.param_space import Categorical, Int, Real

from vamos_studio.backend import runs
from vamos_studio.backend.upstream.vamos_bridge import (
    STUDIO_ONLY_PARAMETERS,
    builtin_space,
    population,
    to_algorithm_config,
    weight_file,
    weight_population,
    weight_populations,
    weights_directory,
)

# Grammar parameters without a counterpart in VAMOS's space, and VAMOS's without one here.
GRAMMAR_ONLY = (
    {"external_archive", "polynomial_eta", "linked_polynomial_eta", "mutation_prob_factor"}
    | set(STUDIO_ONLY_PARAMETERS)
    | {"selection", "reference_point_offset"}
)
VAMOS_ONLY = {"use_external_archive", "archive_unbounded", "mutation_eta", "mutation_prob"}
# VAMOS names that the grammars name as NSGA-II's grammar does (SMS-EMOA's space says "pm").
VALUE_ALIASES = {"pm": "polynomial"}
SPACES = [
    ("moead", "real"),
    ("moead", "binary"),
    ("smsemoa", "real"),
    ("smsemoa", "binary"),
    ("agemoea", "real"),
    ("rvea", "real"),
    ("spea2", "real"),
]


def _front(algorithm: str, config, problem: str, n_obj: int | None = None) -> np.ndarray:
    result = vamos.optimize(
        problem, algorithm=algorithm, algorithm_config=config, n_obj=n_obj,
        max_evaluations=3000, seed=3,
    )  # fmt: skip
    return np.asarray(result.F)


class TestDefaultConfiguration:
    @pytest.mark.parametrize(("problem", "n_obj"), [("zdt1", 2), ("zdt4", 2)])
    def test_should_run_moead_exactly_as_the_vamos_default(self, problem, n_obj):
        # Arrange
        n_var = vamos.make_problem_selection(problem, n_obj=n_obj).n_var
        space = builtin_space("moead", "real")

        # Act
        front = _front(
            "moead", to_algorithm_config(space.default_configuration(), n_var, n_obj), problem
        )

        # Assert
        default = MOEADConfig.default(n_var=n_var, n_obj=n_obj)
        assert np.array_equal(front, _front("moead", default, problem))

    @pytest.mark.parametrize("problem", ["zdt1", "zdt4", "dtlz2"])
    def test_should_run_smsemoa_exactly_as_the_vamos_default(self, problem):
        # Arrange
        selection = vamos.make_problem_selection(problem)
        space = builtin_space("smsemoa", "real")
        config = to_algorithm_config(
            space.default_configuration(), selection.n_var, selection.n_obj
        )

        # Act
        front = _front("smsemoa", config, problem)

        # Assert
        default = SMSEMOAConfig.default(n_var=selection.n_var)
        assert np.array_equal(front, _front("smsemoa", default, problem))

    @pytest.mark.parametrize("problem", ["zdt1", "zdt4", "dtlz2"])
    @pytest.mark.parametrize(
        ("algorithm", "config_class"), [("agemoea", AGEMOEAConfig), ("spea2", SPEA2Config)]
    )
    def test_should_run_agemoea_and_spea2_exactly_as_the_vamos_default(
        self, algorithm, config_class, problem
    ):
        # Arrange
        selection = vamos.make_problem_selection(problem)
        space = builtin_space(algorithm, "real")
        config = to_algorithm_config(
            space.default_configuration(), selection.n_var, selection.n_obj
        )

        # Act
        front = _front(algorithm, config, problem)

        # Assert
        default = config_class.default(n_var=selection.n_var)
        assert np.array_equal(front, _front(algorithm, default, problem))

    @pytest.mark.parametrize(("problem", "n_obj", "pop_size"), [("dtlz2", 3, 91), ("zdt1", 2, 13)])
    def test_should_run_rvea_exactly_as_the_vamos_default(self, problem, n_obj, pop_size):
        # Arrange
        n_var = vamos.make_problem_selection(problem).n_var
        space = builtin_space("rvea", "real")
        config = to_algorithm_config(space.default_configuration(), n_var, n_obj)

        # Act
        front = _front("rvea", config, problem)

        # Assert
        default = RVEAConfig.default(pop_size=pop_size, n_var=n_var, n_obj=n_obj)
        assert config.pop_size == pop_size
        assert np.array_equal(front, _front("rvea", default, problem))

    @pytest.mark.parametrize("algorithm", ["moead", "smsemoa"])
    def test_should_solve_a_binary_problem_with_bits(self, algorithm):
        # Arrange
        config = to_algorithm_config(
            builtin_space(algorithm, "binary").default_configuration(), 50, 2
        )

        # Act
        result = vamos.optimize(
            "bin_knapsack",
            algorithm=algorithm,
            algorithm_config=config,
            max_evaluations=2000,
            seed=1,
        )

        # Assert
        assert set(np.unique(np.asarray(result.X))) <= {0, 1}

    def test_should_need_the_problem_variables_for_the_mutation_probability(self):
        # Act / Assert
        with pytest.raises(ValueError, match="number of variables"):
            to_algorithm_config(builtin_space("moead", "real").default_configuration())


class TestPopulation:
    @pytest.mark.parametrize(
        ("algorithm", "values", "n_obj", "expected"),
        [
            ("rvea", {"n_partitions": 12}, 3, 91),
            ("rvea", {"n_partitions": 12}, 2, 13),
            ("rvea", {"n_partitions": 4}, 8, 330),
            ("moead", {"pop_size": 110}, 3, 100),
            ("moead", {"pop_size": 100}, 6, 100),
            ("spea2", {"pop_size": 60}, 4, 60),
        ],
    )
    def test_should_give_the_population_a_configuration_runs_with(
        self, algorithm, values, n_obj, expected
    ):
        # Act / Assert
        assert population(values, algorithm, n_obj) == expected


class TestWeightVectors:
    """With three or more objectives MOEA/D reads jMetal's weight files, as jMetal and Evolver."""

    @pytest.mark.parametrize(
        ("pop_size", "n_obj", "expected"),
        [
            (100, 2, 100),
            (37, 2, 37),
            (100, 3, 100),
            (91, 3, 91),
            (110, 3, 100),
            (50, 3, 91),
            (200, 3, 136),
        ],
    )
    def test_should_choose_a_population_with_a_weight_file(self, pop_size, n_obj, expected):
        # Act / Assert
        assert weight_population(pop_size, n_obj) == expected

    def test_should_name_the_file_it_reads(self):
        # Act / Assert
        assert weight_file(100, 3) == "W3D_100.dat"
        assert weight_file(100, 2) is None
        assert {91, 100, 136, 300} <= set(weight_populations(3))

    def test_should_read_w3d_100_with_a_population_of_100(self):
        # Arrange
        space = builtin_space("moead", "real")
        config = to_algorithm_config(space.default_configuration(), 12, 3)
        explicit = MOEADConfig.default(n_var=12, n_obj=3)
        explicit = dataclasses.replace(
            explicit,
            pop_size=100,
            weight_vectors={"path": str(weights_directory()), "divisions": None},
        )

        # Act
        front = _front("moead", config, "dtlz2", n_obj=3)

        # Assert
        assert config.pop_size == 100
        assert config.weight_vectors["path"] == str(weights_directory())
        assert np.array_equal(front, _front("moead", explicit, "dtlz2", n_obj=3))

    def test_should_read_the_vectors_of_the_vamos_default_lattice_with_91(self):
        """VAMOS's default lattice for three objectives is W3D_91.dat, to rounding (1e-16)."""
        # Arrange
        from vamos.engine.algorithm.components.weight_vectors import (
            load_or_generate_weight_vectors,
        )

        # Act
        lattice = load_or_generate_weight_vectors(91, 3, divisions=12, mode="jmetalpy")
        read = load_or_generate_weight_vectors(
            91, 3, path=str(weights_directory()), mode="jmetalpy"
        )

        # Assert
        assert weight_population(91, 3) == 91
        assert np.allclose(lattice, read, rtol=0, atol=1e-12)


class TestDriftFromVamos:
    @pytest.mark.parametrize(("algorithm", "encoding"), SPACES)
    def test_should_have_the_same_parameters_as_the_vamos_space(self, algorithm, encoding):
        # Arrange
        vamos_space = _vamos_space(algorithm, encoding)

        # Act
        grammar = {p.name for p in builtin_space(algorithm, encoding).all_parameters()}

        # Assert
        assert grammar - GRAMMAR_ONLY == set(vamos_space.params) - (VAMOS_ONLY - grammar)

    @pytest.mark.parametrize(("algorithm", "encoding"), SPACES)
    def test_should_have_the_same_domains_as_the_vamos_space(self, algorithm, encoding):
        # Arrange
        vamos_space = _vamos_space(algorithm, encoding)

        # Act / Assert
        for parameter in builtin_space(algorithm, encoding).all_parameters():
            if parameter.name not in vamos_space.params:
                continue
            spec = vamos_space.params[parameter.name]
            if isinstance(spec, (Real, Int)):
                assert (parameter.low, parameter.high) == (spec.low, spec.high), parameter.name
            elif isinstance(spec, Categorical):
                choices = [VALUE_ALIASES.get(v, v) for v in spec.choices]
                assert sorted(map(str, parameter.values)) == sorted(map(str, choices)), (
                    parameter.name
                )


def _vamos_space(algorithm: str, encoding: str):
    suffix = "" if encoding == "real" else f"_{encoding}"
    return getattr(bridge_spaces, f"build_{algorithm}{suffix}_config_space")().to_param_space()


class TestRuns:
    def test_should_run_moead_with_three_objectives_on_jmetals_weight_file(self, tmp_path):
        # Arrange
        space = builtin_space("moead", "real")
        request = dataclasses.replace(
            make_request("dtlz2", 3000),
            algorithm="moead",
            space=space.name,
            space_hash=space.content_hash(),
            configuration=dict(space.default_configuration().values),
            n_obj=3,
        )

        # Act
        run = runs.launch(request, tmp_path)
        state = wait_for_end(run)

        # Assert
        manifest = runs.manifest(run)
        assert state == runs.RunState.FINISHED
        assert manifest["resolved_spec"]["algorithm"]["config"]["pop_size"] == 100

    def test_should_end_the_monitor_with_the_result_without_live_archive(self, tmp_path):
        """SMS-EMOA passes no archive to the live callback: the final live front is the result."""
        # Arrange
        space = builtin_space("smsemoa", "real")
        values = space.default_values() | {"external_archive": "bounded"}
        request = dataclasses.replace(
            make_request("zdt1", 3000),
            algorithm="smsemoa",
            space=space.name,
            space_hash=space.content_hash(),
            configuration=dict(space.configuration(values, complete=True).values),
        )

        # Act
        run = runs.launch(request, tmp_path)
        wait_for_end(run)

        # Assert
        live, result = runs.live_front(run), runs.result_front(run)[0]
        assert live.shape == result.shape
        assert np.allclose(np.sort(live, axis=0), np.sort(result, axis=0), rtol=1e-9)

    def test_should_run_rvea_with_three_objectives_and_its_lattice(self, tmp_path):
        # Arrange
        space = builtin_space("rvea", "real")
        values = space.default_values() | {"external_archive": "unbounded"}
        request = dataclasses.replace(
            make_request("dtlz2", 3000),
            algorithm="rvea",
            space=space.name,
            space_hash=space.content_hash(),
            configuration=dict(space.configuration(values, complete=True).values),
            n_obj=3,
        )

        # Act
        run = runs.launch(request, tmp_path)
        state = wait_for_end(run)

        # Assert
        assert state == runs.RunState.FINISHED
        assert runs.manifest(run)["resolved_spec"]["algorithm"]["config"]["pop_size"] == 91
        assert len(runs.result_front(run)[0]) <= 91  # the subset of the archive, as the population
