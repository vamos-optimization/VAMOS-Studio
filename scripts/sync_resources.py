"""Refresh vamos_studio/resources/ from the jMetal release set by JMETAL_VERSION.

Downloads each file of COPIED_FILES and jMetal's license from GitHub, replaces the copy and
rewrites SHA256SUMS. Run it (`make sync-resources`) whenever JMETAL_VERSION or COPIED_FILES
changes.

Adapted from Evolver-Studio (scripts/sync_resources.py), by the same authors.
"""

import shutil
import urllib.request

from vamos_studio.backend.bundled_resources import (
    COPIED_FILES,
    JMETAL_VERSION,
    LICENSE_FILE,
    MANIFEST_FILE,
    RESOURCES_DIRECTORY,
    local_path,
    source_url,
    write_manifest,
)


def _download(source: str, target_name: str) -> None:
    url = source_url(source)
    print(f"Downloading {url}")
    target = RESOURCES_DIRECTORY / target_name
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response:
        target.write_bytes(response.read())


def main() -> None:
    shutil.rmtree(RESOURCES_DIRECTORY / "referenceFronts", ignore_errors=True)
    for source in COPIED_FILES:
        _download(source, local_path(source))
    _download("LICENSE.txt", LICENSE_FILE)
    count = write_manifest()
    print(f"Copied {count} files from jMetal {JMETAL_VERSION}; wrote {MANIFEST_FILE.name}")


if __name__ == "__main__":
    main()
