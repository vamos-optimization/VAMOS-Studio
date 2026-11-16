"""Tests for the light and dark themes: the colours of the figures and the logo follow the theme."""

import tomllib
from pathlib import Path

import numpy as np
import pytest

from vamos_studio import branding, charts, theme

CONFIG = Path(__file__).resolve().parent.parent / ".streamlit" / "config.toml"


@pytest.fixture(params=[False, True], ids=["light", "dark"])
def dark(request, monkeypatch):
    monkeypatch.setattr(charts, "is_dark", lambda: request.param)
    monkeypatch.setattr(branding, "is_dark", lambda: request.param)
    return request.param


class TestTheme:
    def test_should_be_light_outside_a_session(self):
        # Act / Assert
        assert theme.is_dark() is False

    def test_should_define_a_light_and_a_dark_theme_for_the_viewer_to_choose(self):
        # Act
        config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))["theme"]

        # Assert
        assert "base" not in config
        assert {"light", "dark"} <= set(config)


class TestColoursFollowTheTheme:
    def test_should_draw_the_front_and_the_knee_in_the_colours_of_the_theme(self, dark):
        # Arrange
        expected = charts.DARK if dark else charts.LIGHT

        # Act
        figure = charts.front_figure(np.ones((3, 2)), np.zeros((5, 2)), highlighted=1)

        # Assert
        assert [trace.marker.color for trace in figure.data] == [
            expected.reference,
            expected.front,
            expected.selected,
        ]

    def test_should_draw_the_reference_lines_in_the_colour_of_the_theme(self, dark):
        # Arrange
        expected = charts.DARK if dark else charts.LIGHT

        # Act
        figure = charts.parallel_figure([(np.ones((2, 5)), "Front", "blue", 1.0)], np.eye(5))

        # Assert
        assert figure.data[0].line.color == expected.parallel_reference

    def test_should_show_the_wordmark_of_the_theme(self, dark):
        # Act
        shown = branding.wordmark()

        # Assert
        assert shown == (branding.WORDMARK_DARK if dark else branding.WORDMARK)
