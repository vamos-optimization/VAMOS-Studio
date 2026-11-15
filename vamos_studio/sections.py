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
        icon: Its Material icon in the menu and on its card (":material/<name>:").
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
                ":material/account_tree:",
                "Browse VAMOS's multi-objective algorithms and the parameters each one can be "
                "configured with, for each encoding.",
                available=True,
            ),
            Page(
                "pages/explore_problems.py",
                "Problems",
                ":material/extension:",
                "The benchmark and real-world problems available in VAMOS, with their encoding, "
                "objectives, variables and reference fronts.",
                available=True,
            ),
            Page(
                "pages/explore_indicators.py",
                "Quality indicators",
                ":material/straighten:",
                "The quality indicators of VAMOS, what each one measures and how the studio "
                "normalizes fronts, with a sandbox to see how they respond.",
                available=True,
            ),
        ),
    ),
    Section(
        "Optimize",
        (
            Page(
                "pages/new_run.py",
                "New run",
                ":material/play_circle:",
                "Choose a problem and an algorithm, adjust its configuration from the default one, "
                "set the budget and launch the run in the background.",
                available=True,
            ),
            Page(
                "pages/monitor.py",
                "Monitor",
                ":material/monitor_heart:",
                "Follow a run live, with its front as it evolves; stop it keeping what it found, "
                "or cancel it.",
                available=True,
            ),
            Page(
                "pages/history.py",
                "History",
                ":material/history:",
                "Every run with its state, problem, algorithm and budget; open one in the monitor "
                "or in the results.",
                available=True,
            ),
        ),
    ),
    Section(
        "Analyze",
        (
            Page(
                "pages/results.py",
                "Results",
                ":material/insights:",
                "The front a run found, with its knee and extremes, its quality indicators, its "
                "solutions to download, and how VAMOS ran it; for a series of independent runs, "
                "their fronts and union and their indicators with median, spread and best run.",
                available=True,
            ),
        ),
    ),
)
