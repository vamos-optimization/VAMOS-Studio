"""Tests for the text views of a parameter space."""

import pytest

from vamos_studio.backend.upstream.vamos_bridge import builtin_space
from vamos_studio.parameter_tree import parameter_rows, summarize, tree_markdown


@pytest.fixture(scope="module")
def space():
    return builtin_space("nsgaii", "real")


class TestSummary:
    def test_should_count_the_parameters_of_the_nsgaii_grammar(self, space):
        # Act
        summary = summarize(space)

        # Assert
        assert summary.parameters == len(space.all_parameters())
        assert summary.top_level == 8
        assert summary.default_active == 13
        assert summary.depth == 2


class TestTreeMarkdown:
    def test_should_nest_conditional_parameters_under_their_value(self, space):
        # Act
        lines = tree_markdown(space).splitlines()

        # Assert
        sbx = lines.index("    - `sbx`")
        assert lines[sbx + 1].startswith(
            "        - **Distribution index** `sbx_distribution_index`"
        )

    def test_should_list_global_sub_parameters_under_any_value(self, space):
        # Act
        text = tree_markdown(space)

        # Assert
        assert (
            "    - *any value*\n        - **Crossover probability** `crossover_probability`" in text
        )

    def test_should_list_values_without_parameters_together(self, space):
        # Act
        text = tree_markdown(space)

        # Assert
        assert "- values: `auto`, `clip`, `reflect`, `random`, `wrap`, `midpoint`" in text
        assert "- other values: `arithmetic`" in text


class TestParameterRows:
    def test_should_say_when_each_parameter_is_active(self, space):
        # Act
        rows = {row["Parameter"]: row for row in parameter_rows(space)}

        # Assert
        assert rows["pop_size"]["Active when"] == "(root)"
        assert rows["crossover_probability"]["Active when"] == "crossover (any value)"
        assert rows["archive_prune_policy"]["Active when"] == "external_archive = bounded"
        assert len(rows) == len(space.all_parameters())
