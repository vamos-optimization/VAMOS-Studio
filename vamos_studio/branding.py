"""The VAMOS logo in the studio: its files (see resources/branding/README.md)."""

from importlib.resources import files
from typing import Final

BRANDING: Final = files("vamos_studio") / "resources" / "branding"
LOGO: Final = str(BRANDING / "vamos_logo.png")
WORDMARK: Final = str(BRANDING / "vamos_wordmark.png")
MARK: Final = str(BRANDING / "vamos_mark.png")
