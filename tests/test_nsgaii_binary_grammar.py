"""Tests for the NSGA-II grammar for binary-coded problems against VAMOS.

As for the real-coded grammar: its default configuration runs exactly as VAMOS's own default
for binary problems (rule G7), and it describes the same parameters as VAMOS's tuning space.
"""

import numpy as np
import pytest
import vamos
from vamos.algorithms import NSGAIIConfig
from vamos.engine.tuning.racing.bridge_spaces import build_nsgaii_binary_config_space
from vamos.engine.tuning.racing.param_space import Categorical, Int, Real

from vamos_studio.backend.upstream.vamos_bridge import (
    STUDIO_ONLY_PARAMETERS,
    builtin_space,
    to_algorithm_config,
)

GRAMMAR_ONLY = {"external_archive"} | set(STUDIO_ONLY_PARAMETERS)
VAMOS_ONLY = {"use_external_archive", "archive_unbounded"}


@pytest.fixture(scope="module")
def space():
    return builtin_space("nsgaii", "binary")


@pytest.fixture(scope="module")
def vamos_space():
    return build_nsgaii_binary_config_space().to_param_space()


def _front(config, problem: str) -> np.ndarray:
    result = vamos.optimize(
        problem, algorithm="nsgaii", algorithm_config=config, max_evaluations=3000, seed=7
    )
    return np.asarray(result.F)


class TestDefaultConfiguration:
    @pytest.mark.parametrize("problem", ["zdt5", "bin_knapsack", "bin_qubo"])
    def test_should_run_exactly_as_the_vamos_default(self, space, problem):
        """G7: same seed, same front as NSGAIIConfig.default(encoding="binary")."""
        # Arrange
        n_var = vamos.make_problem_selection(problem).n_var
        default = NSGAIIConfig.default(pop_size=100, n_var=n_var, encoding="binary")

        # Act
        front = _front(to_algorithm_config(space.default_configuration()), problem)

        # Assert
        assert np.array_equal(front, _front(default, problem))


class TestDriftFromVamos:
    def test_should_have_the_same_parameters_as_the_vamos_space(self, space, vamos_space):
        # Act
        grammar = {p.name for p in space.all_parameters()} - GRAMMAR_ONLY
        current = set(vamos_space.params) - VAMOS_ONLY

        # Assert
        assert grammar == current

    def test_should_have_the_same_domains_as_the_vamos_space(self, space, vamos_space):
        # Act / Assert
        for parameter in space.all_parameters():
            if parameter.name in GRAMMAR_ONLY:
                continue
            spec = vamos_space.params[parameter.name]
            if isinstance(spec, (Real, Int)):
                assert (parameter.low, parameter.high, parameter.log) == (
                    spec.low,
                    spec.high,
                    spec.log,
                ), parameter.name
            elif isinstance(spec, Categorical):
                assert parameter.values == tuple(spec.choices), parameter.name

    def test_should_activate_each_parameter_under_the_same_value_as_vamos(self, space):
        # Act / Assert
        for block in build_nsgaii_binary_config_space().conditionals or []:
            if block.parent_name == "use_external_archive":
                continue
            production = space.parameter(block.parent_name).production(block.parent_value)
            assert {c.name for c in production.parameters} == {c.name for c in block.params}
