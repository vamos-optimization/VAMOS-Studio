"""Tests for the configuration form's logic, the knee of a front and the front figure."""

import numpy as np
import pytest

from vamos_studio import charts
from vamos_studio.backend.upstream.vamos_bridge import builtin_space
from vamos_studio.configuration_form import (
    active_fields,
    changes,
    configuration_of,
    with_configuration,
)
from vamos_studio.front_summary import knee, summarize


@pytest.fixture(scope="module")
def space():
    return builtin_space("nsgaii", "real")


class TestActiveFields:
    def test_should_show_the_default_branch_at_first(self, space):
        # Act
        fields = active_fields(space, space.default_values())

        # Assert
        assert [f.parameter.name for f in fields] == list(space.default_configuration().values)

    def test_should_follow_the_chosen_value(self, space):
        # Arrange
        values = space.default_values() | {"crossover": "blx_alpha"}

        # Act
        fields = {f.parameter.name: f for f in active_fields(space, values)}

        # Assert
        assert "crossover_alpha" in fields and "crossover_eta" not in fields
        assert (fields["crossover_alpha"].depth, fields["crossover_alpha"].parent) == (
            1,
            "crossover",
        )


class TestChanges:
    def test_should_list_only_active_parameters_that_differ_from_their_default(self, space):
        # Arrange
        values = space.default_values() | {"crossover": "blx_alpha", "crossover_eta": 35.0}

        # Act
        changed = changes(configuration_of(space, values))

        # Assert
        assert [(c.name, c.default, c.value) for c in changed] == [
            ("crossover", "sbx", "blx_alpha")
        ]

    def test_should_restore_a_stored_configuration_over_the_defaults(self, space):
        # Arrange
        stored = {"crossover": "blx_alpha", "crossover_alpha": 0.2}

        # Act
        values = with_configuration(space, stored)

        # Assert
        assert values["crossover_alpha"] == 0.2
        assert values["mutation"] == "polynomial"


class TestFrontSummary:
    FRONT = np.array([[0.0, 1.0], [0.3, 0.3], [1.0, 0.0], [0.6, 0.1]])

    def test_should_mark_the_extremes_and_the_knee(self):
        # Act
        table = summarize(self.FRONT)

        # Assert
        notes = dict(zip(table["solution"], table["note"]))
        assert notes == {0: "best f1", 1: "knee", 3: "", 2: "best f2"}
        assert knee(table) == 1

    def test_should_sort_by_the_first_objective(self):
        # Act
        table = summarize(self.FRONT)

        # Assert
        assert table["f1"].tolist() == sorted(self.FRONT[:, 0])

    def test_should_have_no_knee_for_an_empty_front(self):
        # Act / Assert
        assert knee(summarize(np.empty((0, 2)))) is None


class TestFrontFigure:
    def test_should_draw_the_reference_front_the_front_and_the_knee(self):
        # Act
        figure = charts.front_figure(np.ones((3, 2)), np.zeros((5, 2)), highlighted=1)

        # Assert
        assert [trace.name for trace in figure.data] == ["Reference front", "Front", "Knee"]

    def test_should_draw_only_the_reference_front_before_any_solution(self):
        # Act
        figure = charts.front_figure(None, np.zeros((5, 2)))

        # Assert
        assert [trace.name for trace in figure.data] == ["Reference front"]
