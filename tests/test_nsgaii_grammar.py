"""Tests for the NSGA-II grammar for real-coded problems against VAMOS.

Two checks keep the grammar honest: its default configuration runs exactly as VAMOS's own
default (rule G7 of the design), and it describes the same parameters as VAMOS's tuning space
(drift detection: a change of VAMOS that the grammar has not followed fails here).
"""

import numpy as np
import pytest
import vamos
from vamos.algorithms import NSGAIIConfig
from vamos.engine.tuning.racing.bridge_spaces import build_nsgaii_config_space
from vamos.engine.tuning.racing.param_space import Boolean, Categorical, Int, Real

from vamos_studio.backend.upstream.vamos_bridge import (
    builtin_space,
    to_algorithm_config,
    to_vamos_assignment,
)

# Grammar parameters that have no single counterpart in VAMOS's space (changes M1 and M2).
GRAMMAR_ONLY = {"external_archive", "polynomial_eta", "linked_polynomial_eta"}
VAMOS_ONLY = {"use_external_archive", "archive_unbounded", "mutation_eta"}
EVALUATIONS = 3000
SEED = 7


@pytest.fixture(scope="module")
def space():
    return builtin_space("nsgaii", "real")


@pytest.fixture(scope="module")
def vamos_space():
    return build_nsgaii_config_space().to_param_space()


def _front(config, problem: str) -> np.ndarray:
    result = vamos.optimize(
        problem,
        algorithm="nsgaii",
        algorithm_config=config,
        max_evaluations=EVALUATIONS,
        seed=SEED,
    )
    return np.asarray(result.F)


class TestDefaultConfiguration:
    @pytest.mark.parametrize("problem", ["zdt1", "zdt4"])
    def test_should_run_exactly_as_the_vamos_default(self, space, problem):
        """G7: same seed, same front as NSGAIIConfig.default()."""
        # Arrange
        n_var = vamos.make_problem_selection(problem).n_var
        reference = _front(NSGAIIConfig.default(pop_size=100, n_var=n_var), problem)

        # Act
        front = _front(to_algorithm_config(space.default_configuration()), problem)

        # Assert
        assert np.array_equal(front, reference)


class TestBridge:
    @pytest.mark.parametrize(
        ("choice", "expected"),
        [
            ("none", {"use_external_archive": False}),
            ("unbounded", {"use_external_archive": True, "archive_unbounded": True}),
            ("bounded", {"use_external_archive": True, "archive_unbounded": False}),
        ],
    )
    def test_should_map_the_external_archive_to_the_vamos_switches(self, space, choice, expected):
        # Arrange
        values = space.default_values() | {"external_archive": choice}

        # Act
        assignment = to_vamos_assignment(space.configuration(values, complete=True))

        # Assert
        assert {key: assignment[key] for key in expected} == expected
        assert "external_archive" not in assignment

    @pytest.mark.parametrize("mutation", ["polynomial", "linked_polynomial"])
    def test_should_map_the_distribution_index_back_to_mutation_eta(self, space, mutation):
        # Arrange
        values = space.default_values() | {
            "mutation": mutation,
            "polynomial_eta": 12.0,
            "linked_polynomial_eta": 12.0,
        }

        # Act
        assignment = to_vamos_assignment(space.configuration(values, complete=True))

        # Assert
        assert assignment["mutation_eta"] == 12.0

    def test_should_run_a_configuration_far_from_the_default(self, space):
        # Arrange
        values = space.default_values() | {
            "crossover": "blx_alpha",
            "mutation": "gaussian",
            "external_archive": "bounded",
            "selection": "random",
            "initializer": "lhs",
            "repair": "reflect",
        }
        config = to_algorithm_config(space.configuration(values, complete=True))

        # Act
        front = _front(config, "zdt1")

        # Assert
        assert front.ndim == 2 and front.shape[1] == 2 and len(front) > 0


class TestDriftFromVamos:
    def test_should_have_the_same_parameters_as_the_vamos_space(self, space, vamos_space):
        # Act
        grammar = {p.name for p in space.all_parameters()} - GRAMMAR_ONLY
        current = set(vamos_space.params) - VAMOS_ONLY

        # Assert
        assert grammar == current

    def test_should_have_the_same_domains_as_the_vamos_space(self, space, vamos_space):
        # Arrange
        expected = {"real": Real, "int": Int, "categorical": Categorical, "boolean": Boolean}

        # Act / Assert
        for parameter in space.all_parameters():
            if parameter.name in GRAMMAR_ONLY:
                continue
            spec = vamos_space.params[parameter.name]
            assert isinstance(spec, expected[parameter.type]), parameter.name
            assert _domain_of(spec) == _domain_of_grammar(parameter), parameter.name

    def test_should_split_mutation_eta_without_changing_its_range(self, space, vamos_space):
        # Arrange
        spec = vamos_space.params["mutation_eta"]

        # Act
        ranges = {
            (space.parameter(name).low, space.parameter(name).high)
            for name in ("polynomial_eta", "linked_polynomial_eta")
        }

        # Assert
        assert ranges == {(spec.low, spec.high)}

    def test_should_activate_each_parameter_under_the_same_value_as_vamos(self, space):
        # Arrange
        blocks = build_nsgaii_config_space().conditionals or []

        # Act / Assert
        for block in blocks:
            if block.parent_name == "use_external_archive":
                continue
            production = space.parameter(block.parent_name).production(block.parent_value)
            assert {child.name for child in production.parameters} == {
                child.name for child in block.params
            }, f"{block.parent_name} = {block.parent_value}"


def _domain_of(spec) -> tuple:
    if isinstance(spec, (Real, Int)):
        return (spec.low, spec.high, spec.log)
    if isinstance(spec, Categorical):
        return tuple(spec.choices)
    return ()


def _domain_of_grammar(parameter) -> tuple:
    if parameter.type in ("real", "int"):
        return (parameter.low, parameter.high, parameter.log)
    if parameter.type == "categorical":
        return parameter.values
    return ()
