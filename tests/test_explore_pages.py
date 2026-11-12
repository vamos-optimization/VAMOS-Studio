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
    def test_should_offer_only_nsgaii_for_real_problems(self, algorithms_app: AppTest):
        # Assert
        assert [box.options for box in algorithms_app.selectbox] == [["NSGA-II"], ["Real"]]

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

    def test_should_not_offer_the_binary_zdt5(self):
        # Act
        app = AppTest.from_file(PROBLEMS_PAGE, default_timeout=60).run()

        # Assert
        assert app.selectbox[0].options == ["ZDT"]
        assert "ZDT5" not in app.selectbox[1].options
