"""The adapter between the app and VAMOS: the only package that talks to VAMOS.

Pages and the other modules of `vamos_studio` never import `vamos`; they call this package, so a
change in VAMOS is absorbed here without touching the UI.
"""

from importlib.metadata import PackageNotFoundError, version

VAMOS_DISTRIBUTION = "vamos-optimization"


def vamos_version() -> str | None:
    """Return the installed VAMOS version, without importing VAMOS.

    Returns:
        The version of the `vamos-optimization` distribution, or None if it is not installed.
    """
    try:
        installed = version(VAMOS_DISTRIBUTION)
    except PackageNotFoundError:
        installed = None
    return installed
