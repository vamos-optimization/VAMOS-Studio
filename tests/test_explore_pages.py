"""Tests for the Explore pages, driven through Streamlit's AppTest."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
ALGORITHMS_PAGE = str(ROOT / "pages" / "explore_algorithms.py")
PROBLEMS_PAGE = str(ROOT / "pages" / "explore_problems.py")


@pytest.fixture(scope="module")
def algorithms_app() -> AppTest:
    return AppTest.from_file(ALGORITHMS_PAGE, default_timeout=60).run()


class TestAlgorithmsPage:
    def test_should_offer_the_available_algorithms_starting_at_nsgaii(
        self, algorithms_app: AppTest
    ):
        # Assert
        algorithm, encoding = algorithms_app.selectbox
        assert algorithm.options == [
            "AGE-MOEA",
            "MOEA/D",
            "NSGA-II",
            "NSGA-III",
            "RVEA",
            "SMS-EMOA",
            "SPEA2",
        ]
        assert algorithm.value.label == "NSGA-II"
        assert encoding.options == ["Real", "Binary"]

    def test_should_show_the_default_configuration_as_a_command_line(self, algorithms_app: AppTest):
        # Act
        commands = [block.value for block in algorithms_app.code if block.language == "bash"]

        # Assert
        assert commands[0].startswith("--pop_size 100 --offspring_ratio 1.0 --selection tournament")

    def test_should_show_the_grammar_as_yaml(self, algorithms_app: AppTest):
        # Act
        grammars = [block.value for block in algorithms_app.code if block.language == "yaml"]

        # Assert
        assert grammars[0].startswith("schema: vamos.parameter-space")


class TestProblemsPage:
    @pytest.mark.parametrize("label", ["ZDT1", "ZDT2", "ZDT3", "ZDT4", "ZDT6"])
    def test_should_show_each_available_zdt_problem(self, label: str):
        # Arrange
        app = AppTest.from_file(PROBLEMS_PAGE, default_timeout=60).run()

        # Act
        problems = app.selectbox[1]
        problems.select_index(problems.options.index(label)).run()

        # Assert
        assert not app.exception
        assert app.subheader[0].value == label

    def test_should_offer_the_active_families_and_zdt5(self):
        # Act
        app = AppTest.from_file(PROBLEMS_PAGE, default_timeout=60).run()

        # Assert
        assert app.selectbox[0].options[:2] == ["ZDT", "DTLZ"]
        assert {"Knapsack (binary)", "QUBO (binary)"} <= set(app.selectbox[0].options)
        assert "ZDT5" in app.selectbox[1].options

    @pytest.mark.parametrize("n_obj", [2, 3])
    def test_should_follow_the_objectives_with_the_standard_variables(self, n_obj):
        # Arrange
        app = AppTest.from_file(PROBLEMS_PAGE, default_timeout=60).run()
        app.selectbox[0].select_index(1).run()
        app.selectbox[1].select_index(app.selectbox[1].options.index("DTLZ2")).run()

        next(c for c in app.checkbox if c.label == "Set its arguments").check().run()

        # Act
        next(b for b in app.selectbox if b.label == "Objectives").select(n_obj).run()

        # Assert
        assert not app.exception
        assert [m.value for m in app.metric][:2] == [str(n_obj + 9), str(n_obj)]


INDICATORS_PAGE = str(ROOT / "pages" / "explore_indicators.py")


class TestIndicatorsPage:
    def test_should_offer_only_problems_with_a_reference_front(self):
        # Act
        app = AppTest.from_file(INDICATORS_PAGE, default_timeout=60).run()

        # Assert
        options = next(box for box in app.selectbox if box.label == "Problem").options
        assert "ZDT1" in options and "DTLZ2" in options
        assert "Binary Knapsack" not in options

    def test_should_show_one_row_per_indicator(self):
        # Arrange
        from vamos_studio.backend.indicators import INDICATORS

        # Act
        app = AppTest.from_file(INDICATORS_PAGE, default_timeout=60).run()

        # Assert
        assert not app.exception
        table = next(m.value for m in app.markdown if "| Abbreviation |" in m.value)
        for entry in INDICATORS:
            assert f"| `{entry.key}` |" in table

    def test_should_show_a_value_for_every_available_indicator(self):
        # Act
        app = AppTest.from_file(INDICATORS_PAGE, default_timeout=60).run()

        # Assert
        assert [metric.label for metric in app.metric] == [
            "HV ↑",
            "NHV ↓",
            "IGD ↓",
            "IGD+ ↓",
            "EP ↓",
            "Δp ↓",
        ]

    def test_should_give_zero_distances_for_the_whole_front_unshifted(self):
        # Arrange
        app = AppTest.from_file(INDICATORS_PAGE, default_timeout=60).run()

        # Act
        app.slider[0].set_value(200).run()
        app.slider[1].set_value(0.0).run()

        # Assert
        assert not app.exception
        values = {metric.label: metric.value for metric in app.metric}
        assert float(values["NHV ↓"]) < 0.01
        assert float(values["IGD+ ↓"]) < 0.01

    def test_should_list_the_arguments_of_each_problem(self):
        # Act
        app = AppTest.from_file(PROBLEMS_PAGE, default_timeout=60).run()

        # Assert
        table = app.dataframe[1].value
        assert table.loc[table["Problem"] == "ZDT1", "Arguments"].item() == "n_var: integer = 30"
