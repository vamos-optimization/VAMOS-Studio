"""The VAMOS logo in the studio: its files (see resources/branding/README.md)."""

from importlib.resources import files
from typing import Final

from vamos_studio.theme import is_dark

BRANDING: Final = files("vamos_studio") / "resources" / "branding"
LOGO: Final = str(BRANDING / "vamos_logo.png")
WORDMARK: Final = str(BRANDING / "vamos_wordmark.png")
MARK: Final = str(BRANDING / "vamos_mark.png")
# The full logo on a navy card, which reads on both themes: the home page shows it before the
# studio knows the theme (st.context.theme may be wrong on the first run of a session).
LOGO_CARD: Final = str(BRANDING / "vamos_logo_card.png")
# With the dark theme: the wordmark with its lettering in light tones.
WORDMARK_DARK: Final = str(BRANDING / "vamos_wordmark_dark.png")


def wordmark() -> str:
    """The logo without the tagline, for the theme the viewer sees."""
    return WORDMARK_DARK if is_dark() else WORDMARK
