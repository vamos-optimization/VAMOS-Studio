"""Tests for the app's sections and its home page."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from vamos_studio.sections import HOME_PAGE, SECTIONS

ROOT = Path(__file__).resolve().parent.parent
APP_SCRIPT = ROOT / "app.py"
PAGES = [page for section in SECTIONS for page in section.pages]
PLACEHOLDER_MARK = "Not implemented yet"


class TestSections:
    @pytest.mark.parametrize("path", [HOME_PAGE] + [page.path for page in PAGES])
    def test_should_point_every_page_at_an_existing_script(self, path: str):
        # Assert
        assert (ROOT / path).is_file()

    @pytest.mark.parametrize("page", PAGES, ids=[page.title for page in PAGES])
    def test_should_mark_as_available_exactly_the_pages_that_are_not_placeholders(self, page):
        # Act
        is_placeholder = PLACEHOLDER_MARK in (ROOT / page.path).read_text()

        # Assert
        assert page.available is not is_placeholder


class TestHomePage:
    @pytest.fixture
    def app(self, monkeypatch, tmp_path) -> AppTest:
        monkeypatch.setenv("VAMOS_STUDIO_RUNS", str(tmp_path))
        return AppTest.from_file(str(APP_SCRIPT), default_timeout=30).run()

    def test_should_open_the_app_on_the_home_page_without_exceptions(self, app: AppTest):
        # Assert
        assert not app.exception
        assert app.title[0].value == "Explore, run and analyze"

    def test_should_offer_a_first_run_in_one_click(self, app: AppTest):
        # Assert
        assert any(button.label == "Try NSGA-II on ZDT1" for button in app.button)

    def test_should_show_the_installed_vamos_version(self, app: AppTest):
        # Assert
        assert any(caption.value.startswith("Backend: VAMOS ") for caption in app.caption)

    def test_should_show_every_page_under_its_section(self, app: AppTest):
        # Act
        headings = [
            markdown.value.split(" ", 1)[0] + " " + markdown.value.rsplit(" ", 1)[-1]
            for markdown in app.markdown
            if markdown.value.startswith("####")
        ]

        # Assert
        assert headings == [
            line
            for section in SECTIONS
            for line in (
                f"#### {section.name}",
                *(f"##### {page.title.rsplit(' ', 1)[-1]}" for page in section.pages),
            )
        ]

    def test_should_number_the_steps_of_a_study(self, app: AppTest):
        # Act
        sections = [
            markdown.value for markdown in app.markdown if markdown.value.startswith("#### ")
        ]

        # Assert
        assert [heading.split(" ", 2)[2] for heading in sections] == [
            "1 · Explore",
            "2 · Optimize",
            "3 · Analyze",
            "Learn",
        ]


class TestPages:
    @pytest.mark.parametrize("page", PAGES, ids=[page.title for page in PAGES])
    def test_should_render_every_page_without_exceptions(self, page, monkeypatch, tmp_path):
        """Through the app's navigation, as a user opens it, with no runs yet."""
        # Arrange
        monkeypatch.setenv("VAMOS_STUDIO_RUNS", str(tmp_path))
        app = AppTest.from_file(str(APP_SCRIPT), default_timeout=30).run()

        # Act
        app.switch_page(page.path).run()

        # Assert
        assert not app.exception
        assert app.title[0].value == page.title
