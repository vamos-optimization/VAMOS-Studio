"""Tests for the studio's grammars: VAMOS's own, with the studio's layer, run as VAMOS runs them.

The grammars are VAMOS's built-in ones (vamos/resources/parameter_spaces). The studio adds its
layer (spaces/studio.yaml): the population, the subset selection of an unbounded archive, and the
labels. These tests check that the layer adds only that, that every parameter has a label, and
that each grammar's default configuration runs exactly as its algorithm's default in VAMOS (rule
G7, which VAMOS checks too: here through the studio's bridge).
"""

import dataclasses

import numpy as np
import pytest
import vamos
from conftest import make_request, wait_for_end
from vamos.algorithms import (
    AGEMOEAConfig,
    MOEADConfig,
    NSGAIIConfig,
    NSGAIIIConfig,
    RVEAConfig,
    SMSEMOAConfig,
    SPEA2Config,
)
from vamos.engine.tuning.grammar import builtin_parameter_space

from vamos_studio.backend import runs
from vamos_studio.backend.upstream.vamos_bridge import (
    BUILTIN_SPACES,
    STUDIO_ONLY_PARAMETERS,
    builtin_space,
    population,
    to_algorithm_config,
    to_vamos_assignment,
    vamos_space_name,
    weight_file,
    weight_population,
)

EVALUATIONS = 3000
SEED = 3


def _front(algorithm: str, config, problem: str, n_obj: int | None = None) -> np.ndarray:
    result = vamos.optimize(
        problem, algorithm=algorithm, algorithm_config=config, n_obj=n_obj,
        max_evaluations=EVALUATIONS, seed=SEED,
    )  # fmt: skip
    return np.asarray(result.F)


def _parameters(space) -> dict[str, object]:
    return {parameter.name: parameter for parameter in space.all_parameters()}


def _vamos_parameters(algorithm: str, encoding: str) -> dict[str, object]:
    grammar = builtin_parameter_space(vamos_space_name(algorithm, encoding))
    return {name: grammar.parameter(name) for name in grammar.names()}


class TestStudioLayer:
    @pytest.mark.parametrize(("algorithm", "encoding"), BUILTIN_SPACES)
    def test_should_add_only_the_studio_parameters_to_the_vamos_grammar(self, algorithm, encoding):
        # Arrange
        vamos_grammar = _vamos_parameters(algorithm, encoding)

        # Act
        studio = _parameters(builtin_space(algorithm, encoding))

        # Assert
        assert set(studio) - set(STUDIO_ONLY_PARAMETERS) == set(vamos_grammar)

    @pytest.mark.parametrize(("algorithm", "encoding"), BUILTIN_SPACES)
    def test_should_keep_the_domains_and_defaults_of_the_vamos_grammar(self, algorithm, encoding):
        # Arrange
        vamos_grammar = _vamos_parameters(algorithm, encoding)

        # Act
        studio = _parameters(builtin_space(algorithm, encoding))

        # Assert
        for name, theirs in vamos_grammar.items():
            ours = studio[name]
            assert str(ours.default) == str(theirs.default), name
            if theirs.values is not None:
                assert [str(v) for v in ours.values] == [str(v) for v in theirs.values], name
            else:
                assert (ours.low, ours.high) == tuple(theirs.range), name

    @pytest.mark.parametrize(("algorithm", "encoding"), BUILTIN_SPACES)
    def test_should_label_every_parameter(self, algorithm, encoding):
        # Act
        unlabelled = [
            parameter.name
            for parameter in builtin_space(algorithm, encoding).all_parameters()
            if not parameter.label
        ]

        # Assert
        assert unlabelled == []

    def test_should_put_the_subset_selection_under_an_unbounded_archive(self):
        # Act
        parameter = _parameters(builtin_space("nsgaii", "real"))["archive_subset_selection"]

        # Assert
        assert parameter.default == "farthest"
        assert builtin_space("nsgaii", "real").parameter("external_archive").active_children(
            "unbounded"
        ) == (parameter,)


class TestBridge:
    def test_should_not_pass_the_subset_selection_to_vamos(self):
        # Arrange
        space = builtin_space("nsgaii", "real")
        values = space.default_values() | {"external_archive": "unbounded"}

        # Act
        assignment = to_vamos_assignment(space.configuration(values, complete=True))

        # Assert
        assert "archive_subset_selection" not in assignment
        assert assignment["external_archive"] == "unbounded"

    @pytest.mark.parametrize(("algorithm", "expected"), [("moead", 3), ("nsgaii", None)])
    def test_should_give_the_objectives_to_the_algorithms_that_need_them(self, algorithm, expected):
        # Act
        assignment = to_vamos_assignment(
            builtin_space(algorithm, "real").default_configuration(), 3
        )

        # Assert
        assert assignment.get("n_obj") == expected

    def test_should_run_a_configuration_far_from_the_default(self):
        # Arrange
        space = builtin_space("nsgaii", "real")
        values = space.default_values() | {
            "crossover": "blx_alpha",
            "mutation": "gaussian",
            "external_archive": "bounded",
            "selection": "random",
            "initial_solutions": "lhs",
            "repair": "reflect",
        }

        # Act
        front = _front(
            "nsgaii", to_algorithm_config(space.configuration(values, complete=True)), "zdt1"
        )

        # Assert
        assert front.ndim == 2 and front.shape[1] == 2 and len(front) > 0


class TestDefaultConfiguration:
    @pytest.mark.parametrize("problem", ["zdt1", "zdt4"])
    def test_should_run_nsgaii_exactly_as_the_vamos_default(self, problem):
        # Arrange
        n_var = vamos.make_problem_selection(problem).n_var
        config = to_algorithm_config(builtin_space("nsgaii", "real").default_configuration())

        # Act / Assert
        default = NSGAIIConfig.default(pop_size=100, n_var=n_var)
        assert np.array_equal(_front("nsgaii", config, problem), _front("nsgaii", default, problem))

    @pytest.mark.parametrize("problem", ["zdt1", "zdt4"])
    def test_should_run_moead_exactly_as_the_vamos_default(self, problem):
        # Arrange
        n_var = vamos.make_problem_selection(problem).n_var
        config = to_algorithm_config(
            builtin_space("moead", "real").default_configuration(), n_var, 2
        )

        # Act / Assert
        default = MOEADConfig.default(n_var=n_var, n_obj=2)
        assert np.array_equal(_front("moead", config, problem), _front("moead", default, problem))

    @pytest.mark.parametrize("problem", ["zdt1", "zdt4", "dtlz2"])
    @pytest.mark.parametrize(
        ("algorithm", "config_class"),
        [("smsemoa", SMSEMOAConfig), ("agemoea", AGEMOEAConfig), ("spea2", SPEA2Config)],
    )
    def test_should_run_as_the_vamos_default(self, algorithm, config_class, problem):
        # Arrange
        selection = vamos.make_problem_selection(problem)
        space = builtin_space(algorithm, "real")
        config = to_algorithm_config(
            space.default_configuration(), selection.n_var, selection.n_obj
        )

        # Act / Assert
        default = config_class.default(n_var=selection.n_var)
        assert np.array_equal(
            _front(algorithm, config, problem), _front(algorithm, default, problem)
        )

    def test_should_run_rvea_exactly_as_the_vamos_default_with_its_lattice(self):
        # Arrange
        n_var = vamos.make_problem_selection("dtlz2").n_var
        config = to_algorithm_config(
            builtin_space("rvea", "real").default_configuration(), n_var, 3
        )

        # Act / Assert
        default = RVEAConfig.default(pop_size=91, n_var=n_var, n_obj=3)
        assert config.pop_size == 91
        assert np.array_equal(_front("rvea", config, "dtlz2"), _front("rvea", default, "dtlz2"))

    @pytest.mark.parametrize(("problem", "n_obj"), [("zdt1", None), ("dtlz2", 3), ("dtlz2", 8)])
    def test_should_run_nsgaiii_exactly_as_the_vamos_default(self, problem, n_obj):
        # Arrange
        selection = vamos.make_problem_selection(problem, n_obj=n_obj)
        n_var, objectives = int(selection.n_var), int(selection.n_obj)
        space = builtin_space("nsgaiii", "real")
        config = to_algorithm_config(space.default_configuration(), n_var, objectives)

        # Act / Assert
        default = NSGAIIIConfig.default(pop_size=100, n_var=n_var, n_obj=objectives)
        assert np.array_equal(
            _front("nsgaiii", config, problem, n_obj), _front("nsgaiii", default, problem, n_obj)
        )

    @pytest.mark.parametrize("algorithm", ["nsgaii", "moead", "smsemoa"])
    def test_should_solve_a_binary_problem_with_bits(self, algorithm):
        # Arrange
        config = to_algorithm_config(
            builtin_space(algorithm, "binary").default_configuration(), 50, 2
        )

        # Act
        result = vamos.optimize(
            "bin_knapsack", algorithm=algorithm, algorithm_config=config,
            max_evaluations=2000, seed=1,
        )  # fmt: skip

        # Assert
        assert set(np.unique(np.asarray(result.X))) <= {0, 1}


class TestPopulation:
    @pytest.mark.parametrize(
        ("algorithm", "values", "n_obj", "expected"),
        [
            ("rvea", {"pop_size": 100}, 3, 91),
            ("rvea", {"pop_size": 100}, 2, 100),
            ("rvea", {"pop_size": 200}, 8, 120),
            ("rvea", {"n_partitions": 12}, 3, 91),  # a run saved before VAMOS 1.4
            ("moead", {"pop_size": 110}, 3, 105),
            ("moead", {"pop_size": 100}, 3, 100),
            ("moead", {"pop_size": 100}, 6, 56),
            ("spea2", {"pop_size": 60}, 4, 60),
        ],
    )
    def test_should_give_the_population_a_configuration_runs_with(
        self, algorithm, values, n_obj, expected
    ):
        # Act / Assert
        assert population(values, algorithm, n_obj) == expected

    @pytest.mark.parametrize(
        ("pop_size", "n_obj", "expected"),
        [
            (100, 2, None),
            (100, 3, "W3D_100.dat"),
            (91, 3, None),
            (100, 4, "W4D_100.dat"),
            (165, 4, None),
            (156, 8, "W8D_156.dat"),
        ],
    )
    def test_should_name_the_weight_file_moead_reads(self, pop_size, n_obj, expected):
        # Act / Assert
        assert weight_file(pop_size, n_obj) == expected

    def test_should_run_the_population_the_bridge_announces(self):
        # Act
        config = to_algorithm_config(
            builtin_space("moead", "real").configuration(
                builtin_space("moead", "real").default_values() | {"pop_size": 150},
                complete=True,
            ),
            12,
            3,
        )

        # Assert
        assert config.pop_size == weight_population(150, 3) == 136


class TestBoundedArchive:
    def test_should_be_as_large_as_the_population(self):
        # Arrange
        space = builtin_space("nsgaii", "real")
        values = space.default_values() | {"pop_size": 60, "external_archive": "bounded"}

        # Act
        config = to_algorithm_config(space.configuration(values, complete=True)).to_dict()

        # Assert
        assert config["external_archive"]["capacity"] == config["pop_size"] == 60

    @pytest.mark.parametrize("archive", ["bounded", "unbounded"])
    def test_should_make_vamos_return_the_archive_and_not_the_population(self, archive):
        # Arrange
        space = builtin_space("nsgaii", "real")
        values = space.default_values() | {"external_archive": archive}
        config = to_algorithm_config(space.configuration(values, complete=True))

        # Act
        result = vamos.optimize(
            "zdt1", algorithm="nsgaii", algorithm_config=config, max_evaluations=10000, seed=1
        )

        # Assert
        assert np.array_equal(np.asarray(result.F), result.data["archive"]["F"])
        if archive == "unbounded":
            assert len(result.F) > len(result.data["population"]["F"])


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
        resolved = runs.manifest(run)["resolved_spec"]["algorithm"]
        assert state == runs.RunState.FINISHED
        assert resolved["config"]["pop_size"] == 100
        assert "W3D_100.dat" in str(resolved)

    def test_should_end_the_monitor_with_the_result_without_live_archive(self, tmp_path):
        """SMS-EMOA sends a final generation: the last live front is the result."""
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
