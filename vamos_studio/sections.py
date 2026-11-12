"""The app's pages, grouped by purpose: the single source of the menu and the home page.

`app.py` builds `st.navigation` from `SECTIONS`, and the home page (`pages/home.py`) shows a card
for each page, so the two cannot drift apart.
"""

from dataclasses import dataclass

HOME_PAGE = "pages/home.py"


@dataclass(slots=True, frozen=True)
class Page:
    """A page of the app.

    Attributes:
        path: Its script, relative to the app's root (e.g. "pages/solve.py").
        title: Its title in the menu and on its card.
        icon: Its icon in the menu and on its card.
        description: What it does, for its card on the home page.
        available: Whether it is implemented, or only a placeholder.
    """

    path: str
    title: str
    icon: str
    description: str
    available: bool


@dataclass(slots=True, frozen=True)
class Section:
    """A group of pages in the menu.

    Attributes:
        name: Its heading in the menu, and the label of its pages' cards on the home page.
        pages: Its pages, in menu order.
    """

    name: str
    pages: tuple[Page, ...]


SECTIONS = (
    Section(
        "Explore",
        (
            Page(
                "pages/explore_algorithms.py",
                "Algorithms",
                "🧬",
                "Browse VAMOS's multi-objective algorithms and the parameters each one can be "
                "configured with, for each encoding.",
                available=True,
            ),
            Page(
                "pages/explore_problems.py",
                "Problems",
                "🧩",
                "The benchmark and real-world problems available in VAMOS, with their encoding, "
                "objectives, variables and reference fronts.",
                available=True,
            ),
            Page(
                "pages/explore_indicators.py",
                "Quality indicators",
                "📏",
                "The quality indicators used to assess the fronts, and what each one measures.",
                available=False,
            ),
        ),
    ),
    Section(
        "Solve",
        (
            Page(
                "pages/solve.py",
                "Run algorithm",
                "▶️",
                "Choose a problem and an algorithm, start from its default configuration and "
                "adjust it, run it with a live view of the front, and inspect the result.",
                available=False,
            ),
        ),
    ),
)
