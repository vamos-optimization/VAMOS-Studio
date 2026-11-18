"""Tests for the backend adapter's entry points."""

from importlib.metadata import PackageNotFoundError

import pytest

from vamos_studio import backend


class TestVamosVersion:
    def test_should_return_the_installed_version(self):
        # Act
        installed = backend.vamos_version()

        # Assert
        assert installed is not None
        assert installed.startswith("1.4")

    def test_should_return_none_when_vamos_is_not_installed(self, monkeypatch: pytest.MonkeyPatch):
        # Arrange
        def missing(_: str) -> str:
            raise PackageNotFoundError

        monkeypatch.setattr(backend, "version", missing)

        # Act
        installed = backend.vamos_version()

        # Assert
        assert installed is None
