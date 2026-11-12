"""The resource files copied from jMetal into vamos_studio/resources/.

The studio measures fronts against jMetal's reference fronts, the same files Evolver and
Evolver-Studio use, so that its indicator values match theirs. VAMOS 1.1 ships inaccurate samples
of some of them (see docs/design/parameter-spaces.md and UPSTREAM.md). They are copied, unchanged,
from the jMetal release `JMETAL_VERSION` by scripts/sync_resources.py, which also records their
checksums in SHA256SUMS.

Adapted from Evolver-Studio (evolver_studio/bundled_resources.py), by the same authors.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Final

JMETAL_VERSION: Final = "7.11"
JMETAL_REPOSITORY: Final = "jMetal/jMetal"
RESOURCES_DIRECTORY: Final = Path(__file__).resolve().parent.parent / "resources"
MANIFEST_FILE: Final = RESOURCES_DIRECTORY / "SHA256SUMS"
# The license of the copied files, kept beside them as the MIT license requires.
LICENSE_FILE: Final = "LICENSE-jMetal.txt"
# Files copied from jMetal, as paths relative to its repository root and to RESOURCES_DIRECTORY.
COPIED_FILES: Final = tuple(
    [f"resources/referenceFronts/ZDT{number}.csv" for number in (1, 2, 3, 4, 6)]
    + [
        f"resources/referenceFronts/DTLZ{number}.{n_obj}D.csv"
        for number in range(1, 8)
        for n_obj in (2, 3)
    ]
)


def local_path(source: str) -> str:
    """Where a file copied from jMetal lives, relative to RESOURCES_DIRECTORY.

    Args:
        source: Its path in jMetal's repository, like "resources/referenceFronts/ZDT4.csv".

    Returns:
        Its path without jMetal's leading "resources/", like "referenceFronts/ZDT4.csv".
    """
    return source.removeprefix("resources/")


def source_url(source: str) -> str:
    """The URL of a file of jMetal's repository at release JMETAL_VERSION."""
    return f"https://raw.githubusercontent.com/{JMETAL_REPOSITORY}/v{JMETAL_VERSION}/{source}"


def copied_files(resources_directory: Path = RESOURCES_DIRECTORY) -> list[str]:
    """The files of the copy present in `resources_directory`, relative to it, sorted."""
    return sorted(
        path.relative_to(resources_directory).as_posix()
        for path in resources_directory.rglob("*")
        if path.is_file() and path.suffix in (".csv", ".txt")
    )


def sha256(path: Path) -> str:
    """The SHA-256 hex digest of a file's content."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_manifest(manifest_file: Path = MANIFEST_FILE) -> dict[str, str]:
    """The SHA-256 digest of each file listed in a SHA256SUMS manifest, by relative path."""
    return {
        name: digest
        for digest, name in (line.split("  ", 1) for line in manifest_file.read_text().splitlines())
    }


def write_manifest(
    resources_directory: Path = RESOURCES_DIRECTORY, manifest_file: Path = MANIFEST_FILE
) -> int:
    """Record the checksum of every copied file in a SHA256SUMS manifest.

    Returns:
        The number of files recorded.
    """
    names = copied_files(resources_directory)
    lines = [f"{sha256(resources_directory / name)}  {name}" for name in names]
    manifest_file.write_text("\n".join(lines) + "\n")
    return len(names)


def reference_front_file(problem: str, n_obj: int) -> Path | None:
    """The copied jMetal reference front of a problem with `n_obj` objectives, if there is one.

    jMetal names the fronts of problems with a fixed number of objectives after the problem
    ("ZDT4.csv") and the others after the number too ("DTLZ2.3D.csv").
    """
    directory = RESOURCES_DIRECTORY / "referenceFronts"
    for name in (f"{problem.upper()}.{n_obj}D.csv", f"{problem.upper()}.csv"):
        if (directory / name).is_file():
            return directory / name
    return None
