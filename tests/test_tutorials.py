"""Tests for the tutorials: their catalogue, and every tutorial walked through in the app."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from vamos_studio import (
    tutorial_parameter_spaces,
    tutorial_reading_fronts,
    tutorial_solving,
    tutorial_tour,
)
from vamos_studio.backend import runs
from vamos_studio.tutorial_runs import notebook_text
from vamos_studio.tutorials import (
    TUTORIALS,
    VAMOS_TUTORIALS,
    TutorialLevel,
    tutorials_by_level,
)

APP = str(Path(__file__).resolve().parent.parent / "app.py")
TUTORIALS_PAGE = "pages/tutorials.py"
STEPS = {
    "tour": tutorial_tour.STEPS,
    "solving": tutorial_solving.STEPS,
    "reading_fronts": tutorial_reading_fronts.STEPS,
    "parameter_spaces": tutorial_parameter_spaces.STEPS,
}


def open_tutorial(slug: str) -> AppTest:
    app = AppTest.from_file(APP, default_timeout=120).run()
    app.switch_page(TUTORIALS_PAGE).run()
    next(button for button in app.button if button.key == f"tutorial_open_{slug}").click().run()
    return app


def go_to_step(app: AppTest, title: str) -> AppTest:
    while app.subheader[0].value != title:
        next(button for button in app.button if button.label == "Next →").click().run()
    return app


class TestCatalogue:
    def test_should_number_the_written_tutorials_consecutively_in_catalogue_order(self):
        # Act
        numbers = [item.number for item in TUTORIALS if item.number is not None]

        # Assert
        assert numbers == [f"S{index}" for index in range(1, len(numbers) + 1)]

    def test_should_have_the_basic_tutorials_written(self):
        # Act
        available = [item.slug for item in TUTORIALS if item.available]

        # Assert
        assert available == ["tour", "solving", "reading_fronts", "parameter_spaces"]
        assert all(item.level is TutorialLevel.BASIC for item in TUTORIALS if item.available)

    def test_should_give_steps_to_every_written_tutorial(self):
        # Act / Assert
        assert {item.slug for item in TUTORIALS if item.available} == set(STEPS)

    def test_should_identify_every_tutorial_by_a_distinct_topic(self):
        # Act
        slugs = [item.slug for item in TUTORIALS]

        # Assert
        assert len(slugs) == len(set(slugs))

    def test_should_pair_only_with_tutorials_vamos_has(self):
        # Act
        paired = {number for item in TUTORIALS for number in item.pairs_with}

        # Assert
        assert paired <= set(VAMOS_TUTORIALS)

    @pytest.mark.parametrize("level", list(TutorialLevel))
    def test_should_group_every_tutorial_under_its_level(self, level):
        # Act
        grouped = tutorials_by_level(level)

        # Assert
        assert grouped and all(item.level is level for item in grouped)

    def test_should_ship_the_notebook_of_every_tutorial_that_names_one(self):
        # Act
        notebooks = [item.notebook for item in TUTORIALS if item.notebook]

        # Assert
        assert notebooks
        assert all(notebook_text(name).startswith("{") for name in notebooks)


class TestWalkThrough:
    def test_should_list_the_tutorials_by_level(self):
        # Act
        app = AppTest.from_file(APP, default_timeout=60).run().switch_page(TUTORIALS_PAGE).run()

        # Assert
        assert not app.exception
        assert [header.value for header in app.subheader] == [
            level.value for level in TutorialLevel
        ]

    @pytest.mark.parametrize("slug", list(STEPS))
    def test_should_render_every_step_without_exceptions(self, slug, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))
        app = open_tutorial(slug)

        # Act
        titles = []
        for _ in STEPS[slug]:
            titles.append(app.subheader[0].value)
            assert not app.exception, titles[-1]
            following = next(button for button in app.button if button.label == "Next →")
            if not following.disabled:
                following.click().run()

        # Assert
        assert titles == [step.title for step in STEPS[slug]]

    def test_should_run_nsgaii_on_zdt1_and_find_the_values_announced(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))
        app = go_to_step(open_tutorial("solving"), "Step 2: NSGA-II with its default configuration")

        # Act
        next(b for b in app.button if b.label.startswith("Run it here")).click().run()

        # Assert
        assert not app.exception
        assert any(s.value.startswith("The values announced") for s in app.success)
        assert len(runs.list_runs(tmp_path)) == 1

    def test_should_measure_an_approximation_on_the_front(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))
        app = go_to_step(open_tutorial("reading_fronts"), "Step 2: measuring an approximation")

        # Act
        app.slider(key="tutorial_reading_fronts_points").set_value(100).run()

        # Assert
        values = {metric.label: float(metric.value) for metric in app.metric}
        assert not app.exception
        assert values["IGD+ ↓"] < 0.01 and values["HV ↑"] > 0.65

    def test_should_activate_the_parameters_of_the_crossover_chosen(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.setenv(runs.RUNS_DIRECTORY_ENV, str(tmp_path))
        app = go_to_step(open_tutorial("parameter_spaces"), "Step 2: choices activate parameters")

        # Act
        app.selectbox(key="tutorial_parameter_spaces_crossover").set_value("blx_alpha").run()

        # Assert
        text = "\n".join(block.value for block in app.markdown)
        assert not app.exception
        assert "crossover_alpha" in text and "crossover_eta" not in text
