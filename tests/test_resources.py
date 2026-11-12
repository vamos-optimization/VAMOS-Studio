"""Tests that the files copied from jMetal (vamos_studio/resources/) match their manifest.

Adapted from Evolver-Studio (tests/test_resources.py), by the same authors.
"""

from pathlib import Path

from vamos_studio.backend.bundled_resources import (
    COPIED_FILES,
    LICENSE_FILE,
    RESOURCES_DIRECTORY,
    copied_files,
    local_path,
    read_manifest,
    reference_front_file,
    sha256,
    source_url,
    write_manifest,
)


class TestPaths:
    def test_should_drop_jmetal_resources_prefix(self):
        # Act / Assert
        assert local_path("resources/referenceFronts/ZDT4.csv") == "referenceFronts/ZDT4.csv"

    def test_should_point_at_the_pinned_jmetal_release(self):
        # Act
        url = source_url("resources/referenceFronts/ZDT4.csv")

        # Assert
        assert url == (
            "https://raw.githubusercontent.com/jMetal/jMetal/v7.11/resources/referenceFronts/ZDT4.csv"
        )

    def test_should_find_the_front_of_a_supported_problem_only(self):
        # Act / Assert
        assert reference_front_file("zdt4").name == "ZDT4.csv"
        assert reference_front_file("dtlz2") is None


class TestManifest:
    def test_should_round_trip_the_checksums_of_the_copied_files(self, tmp_path: Path):
        # Arrange
        (tmp_path / "referenceFronts").mkdir()
        (tmp_path / "referenceFronts" / "ZDT4.csv").write_text("0.0,1.0\n")
        manifest_file = tmp_path / "SHA256SUMS"

        # Act
        count = write_manifest(tmp_path, manifest_file)

        # Assert
        assert count == 1
        assert read_manifest(manifest_file) == {
            "referenceFronts/ZDT4.csv": sha256(tmp_path / "referenceFronts" / "ZDT4.csv")
        }


class TestCopiedResources:
    """The copy in this repository, against the manifest scripts/sync_resources.py wrote."""

    def test_should_hold_exactly_the_files_of_the_manifest(self):
        """A file lost or added by hand would go unnoticed otherwise."""
        # Act / Assert
        assert copied_files() == sorted(read_manifest())

    def test_should_hold_every_copied_file_and_jmetals_license(self):
        # Act
        expected = sorted([local_path(source) for source in COPIED_FILES] + [LICENSE_FILE])

        # Assert
        assert sorted(read_manifest()) == expected

    def test_should_keep_every_file_unchanged(self):
        """Edited copies would no longer be jMetal's; refresh them with `make sync-resources`."""
        # Act
        changed = [
            name
            for name, digest in read_manifest().items()
            if sha256(RESOURCES_DIRECTORY / name) != digest
        ]

        # Assert
        assert changed == []
