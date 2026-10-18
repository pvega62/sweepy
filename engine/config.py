from __future__ import annotations

import copy
import logging
import math
import os
import re
import shutil
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

import questionary
import yaml
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings, merge_key_bindings
from prompt_toolkit.key_binding.key_processor import KeyPress
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style as PromptStyle

from engine.adapters import ADAPTERS
from engine.documents import CONVERTIBLE_SUFFIXES, SUPPORTED_SUFFIXES, convert_to_pdf
from engine.engine_defaults import (
    DEFAULT_APIFY_ACTOR,
    DEFAULT_HIREHUNT_SOURCES,
    DEFAULT_JOBDROP_SITES,
    DEFAULT_JOBSPY_SITES,
    DEFAULT_OPENROLES_ATS,
)
from engine.engines import (
    ENGINE_CATALOG,
    engine_status,
    install_command,
    install_engines,
    missing_engines,
    scrapes_table,
    status_table,
)
from engine.logging import recent_log_lines
from engine.sweep_config import legacy_profile_notice, normalize_sources, validate_sources
from engine.updater import update_sweepy

log = logging.getLogger("sweepy.engine.config")

DOCS_URL = "https://pvega62.github.io/software/docs/category/sweepy"
README_URL = "https://github.com/pvega62/sweepy/blob/main/README.md"

_MENU_WIDTH = 62
_LAST_PROFILE_FILE = os.path.join("profiles", ".last_profile")


def _console_supports(text: str) -> bool:
    """Report whether the active console encoding can render ``text``."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        text.encode(encoding)
        return True
    except (LookupError, UnicodeEncodeError):
        return False


BACK_LABEL = "← Back" if _console_supports("←") else "< Back"


class _GoBack(KeyboardInterrupt):
    """Esc pressed: leave this level and return to the menu above it.

    Subclasses ``KeyboardInterrupt`` so callers that only know the old cancel
    semantics still treat it as a cancelled prompt.
    """


_MENU_STYLE = questionary.Style(
    [
        ("qmark", "fg:#fbbf24 bold"),
        ("question", "fg:#e0f2fe bold"),
        ("answer", "fg:#34d399 bold"),
        ("pointer", "fg:#fbbf24 bold"),
        ("highlighted", "fg:#38bdf8 bold"),
        ("instruction", "fg:#94a3b8 italic"),
        ("text", "fg:#e2e8f0"),
        ("disabled", "fg:#64748b italic"),
    ]
)
_NO_COLOR_STYLE = questionary.Style(
    [
        (name, "")
        for name in (
            "qmark",
            "question",
            "answer",
            "pointer",
            "highlighted",
            "instruction",
            "text",
            "disabled",
        )
    ]
)
_COMMAND_HELP = [
    ("python swee.py", "Open this wizard's main menu"),
    ("python swee.py --run", "Sweep with your last saved profile"),
    ("python swee.py --profile FILE", "Sweep with one profile"),
    ("python swee.py --setup", "Open the wizard directly"),
    ("python swee.py --docx FILE", "Convert a DOCX resume to PDF"),
    ("python swee.py --convert FILE", "Convert any supported document to PDF"),
    ("python swee.py --version", "Show the engine and its dependencies"),
    ("python swee.py --debug", "Write a detailed log under logs/"),
    ("python swee.py --logs", "Print the newest log entries"),
    ("python swee.py --update", "Pull the latest code and dependencies"),
    ("python swee.py --check-update", "Report whether a newer version exists"),
    ("python swee.py --list-engines", "Show every engine and its install status"),
    ("python swee.py --install-engines X", "Download optional engines (all or a list)"),
]


def _hyperlink(label: str, url: str) -> str:
    """Emit an OSC 8 terminal hyperlink, or plain text when the terminal lacks support."""
    if not sys.stdout.isatty():
        return f"{label} ({url})"
    return f"\x1b]8;;{url}\x1b\\{label}\x1b]8;;\x1b\\"


def _boxed(lines: List[str], width: int = _MENU_WIDTH) -> List[str]:
    """Wrap text lines in a Unicode box with a fixed inner width."""
    body = [f"│{('  ' + line).ljust(width)[:width]}│" for line in lines]
    return ["┌" + "─" * width + "┐", *body, "└" + "─" * width + "┘"]


def _color(text: str, ansi_code: str) -> str:
    """Add terminal color when the output supports it and the user has not disabled it."""
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR") is not None:
        return text
    return f"\x1b[{ansi_code}m{text}\x1b[0m"


def _centered_box(lines: List[str], width: int = _MENU_WIDTH) -> List[str]:
    """Center text inside a double-line welcome panel."""
    return [
        "╔" + "═" * width + "╗",
        *(f"║{line.center(width)}║" for line in lines),
        "╚" + "═" * width + "╝",
    ]


def _print_welcome_banner() -> None:
    """Show Sweepy's colorful welcome panel before opening the main menu."""
    _out(_color("       ✦          ·          ✧          ·          ✦", "38;5;220;1"))
    letters = [
        ["████", "█   ", "████", "   █", "████"],
        ["█   █", "█   █", "█ █ █", "██ ██", "█   █"],
        ["████", "█   ", "███ ", "█   ", "████"],
        ["████", "█   ", "███ ", "█   ", "████"],
        ["████", "█  █", "████", "█   ", "█   "],
        ["█   █", "█   █", " █ █ ", "  █  ", "  █  "],
    ]
    logo = ["  ".join(letter[row] for letter in letters) for row in range(5)]
    banner = _centered_box(
        [
            *logo,
            "S W E E P Y",
            "Search smarter, better, faster, stronger.",
            "Modern job searching requires modern solutions.",
        ]
    )
    for index, line in enumerate(banner):
        if index in (0, len(banner) - 1):
            color = "38;5;220;1"
        elif 1 <= index <= 5:
            color = ("38;5;45;1", "38;5;81;1", "38;5;39;1", "38;5;75;1", "38;5;45;1")[index - 1]
        elif index == 6:
            color = "38;5;220;1"
        elif index == 7:
            color = "38;5;129;1"
        else:
            color = "38;5;81"
        _out(_color(line, color))
    slogan = "KNICKS IN FIVE"
    centered_slogan = slogan.center(_MENU_WIDTH + 2)
    slogan_start = centered_slogan.index(slogan)
    _out(
        _color(centered_slogan[:slogan_start], "38;5;81")
        + _color("KNICKS ", "38;5;208;1")
        + _color("IN FIVE", "38;5;33;1")
        + _color(centered_slogan[slogan_start + len(slogan):], "38;5;81")
    )
    print()


def _button_choices(choices: List[str]) -> List[questionary.Choice]:
    """Keep each selectable action in a consistent square-bracket button."""
    button_width = max((len(choice) for choice in choices), default=0)
    return [
        questionary.Choice(title=f"[ {choice:<{button_width}} ]", value=choice)
        for choice in choices
    ]


class _WizardMenuQuestion:
    """Adapt a prompt_toolkit application to the wizard's existing ask helper."""

    def __init__(self, application: Application):
        self.application = application

    def unsafe_ask(self):
        return self.application.run()


def _wizard_menu_select(
    profile_data: Optional[Dict] = None,
    *,
    input=None,
    output=None,
):
    """Build the two-column action dashboard with arrow-key tile navigation."""
    actions = _MENU_TILES
    selected = [0]
    terminal_width = shutil.get_terminal_size(fallback=(80, 24)).columns
    width = max(32, min(92, terminal_width - 2))
    card_width = (width - 9) // 2
    columns = 2
    if terminal_width < 70:
        columns = 1
        card_width = width - 6

    def render():
        fragments = []

        def line(text="", style="class:muted"):
            fragments.append((style, text + "\n"))

        line("╭" + "─" * (width - 2) + "╮", "class:frame")
        line("│  " + "SWEEPY  /  SEARCH LAUNCHPAD"[: width - 5].ljust(width - 4) + "│", "class:heading")
        line("├" + "─" * (width - 2) + "┤", "class:frame")
        for row in range(0, len(actions), columns):
            row_actions = actions[row : row + columns]
            row_indices = list(range(row, row + len(row_actions)))
            # Center a lone trailing tile so an odd tile count still looks balanced.
            lead = 0
            if len(row_actions) == 1 and columns > 1:
                lead = max(0, (width - 4 - card_width) // 2)
            rendered_cards = []
            for index, action in zip(row_indices, row_actions):
                card_fragments = []

                def card_line(text, style):
                    card_fragments.append((style, text))

                number, title, description, _ = action
                is_selected = index == selected[0]
                style = "class:tile.selected" if is_selected else "class:tile"
                inner_width = card_width - 2
                card_line("╭" + "─" * inner_width + "╮", style)
                card_line(
                    "│" + f" {number}  {title}"[: inner_width - 1].ljust(inner_width) + "│",
                    style,
                )
                card_line(
                    "│" + f" {description}"[: inner_width - 1].ljust(inner_width) + "│",
                    style,
                )
                card_line("╰" + "─" * inner_width + "╯", style)
                rendered_cards.append(card_fragments)

            for line_number in range(4):
                fragments.append(("class:frame", "│  "))
                if lead:
                    fragments.append(("class:frame", " " * lead))
                for column, card_fragments in enumerate(rendered_cards):
                    style, text = card_fragments[line_number]
                    fragments.append((style, text))
                    if column == 0 and len(rendered_cards) > 1:
                        fragments.append(("class:frame", "   "))
                padding = width - 4 - lead - (
                    card_width * len(rendered_cards)
                    + (3 if len(rendered_cards) > 1 else 0)
                )
                fragments.append(("class:frame", " " * max(0, padding) + "│\n"))

        if profile_data:
            name = profile_data.get("name") or "(unnamed)"
            titles = (profile_data.get("search") or {}).get("titles") or []
            resume_path = (profile_data.get("resume") or {}).get("path")
            status = (
                f"Current profile: {name}  /  {len(titles)} "
                f"{'title' if len(titles) == 1 else 'titles'}  /  "
                f"{'Ready' if resume_path else 'Resume missing'}"
            )
        else:
            status = "Current profile: none loaded  /  Build one to start"
        line("├" + "─" * (width - 2) + "┤", "class:frame")
        line("│  " + status[: width - 5].ljust(width - 4) + "│", "class:status")
        line(
            "│  "
            + "↑ ↓ ← → navigate   Enter select   Esc exit"[: width - 5].ljust(width - 4)
            + "│",
            "class:muted",
        )
        line("╰" + "─" * (width - 2) + "╯", "class:frame")
        return fragments

    bindings = KeyBindings()

    def move_selection(event, direction):
        row, column = divmod(selected[0], columns)
        if direction == "left":
            column = max(0, column - 1)
        elif direction == "right":
            column = min(columns - 1, column + 1)
        elif direction == "up":
            row = max(0, row - 1)
        elif direction == "down":
            row = min((len(actions) - 1) // columns, row + 1)
        selected[0] = min(row * columns + column, len(actions) - 1)
        event.app.invalidate()

    for key, direction in (
        (Keys.Left, "left"),
        (Keys.Right, "right"),
        (Keys.Up, "up"),
        (Keys.Down, "down"),
    ):
        bindings.add(key)(lambda event, direction=direction: move_selection(event, direction))

    @bindings.add(Keys.Enter)
    @bindings.add(Keys.ControlM)
    def select_action(event):
        event.app.exit(result=actions[selected[0]][3])

    style = PromptStyle.from_dict(
        {}
        if os.environ.get("NO_COLOR") is not None
        else {
            "frame": "fg:#38bdf8",
            "heading": "fg:#e879f9 bold",
            "muted": "fg:#94a3b8",
            "status": "fg:#34d399 bold",
            "tile": "fg:#38bdf8",
            "tile.selected": "fg:#111827 bg:#fbbf24 bold",
        }
    )
    application = Application(
        layout=Layout(Window(FormattedTextControl(render), wrap_lines=False)),
        key_bindings=bindings,
        style=style,
        full_screen=False,
        erase_when_done=False,
        input=input,
        output=output,
    )
    return _WizardMenuQuestion(application)


def _select(message: str, choices: List[str], **kwargs):
    """Create a consistently colored, button-style selection prompt."""
    return questionary.select(
        message,
        choices=_button_choices(choices),
        style=_NO_COLOR_STYLE if os.environ.get("NO_COLOR") is not None else _MENU_STYLE,
        **kwargs,
    )


def _out(text: str) -> None:
    """Print one line, degrading to the console encoding instead of raising."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(text.encode(encoding, "replace").decode(encoding, "replace"))


def _print_nav_help() -> None:
    """Print the wizard controls, the command flags, and the documentation links."""
    for line in _boxed(["Sweepy help"]):
        _out(line)
    print("Controls")
    print("  Esc             Go back one level")
    print("  Ctrl+C          Quit Sweepy")
    print("  Enter or Tab    Accept the current value and advance")
    print("  Arrow keys      Move between tiles and choices")
    print("")
    print("Commands")
    for flag, description in _COMMAND_HELP:
        print(f"  {flag:<32}{description}")
    print("")
    print("Bonus tools")
    print("  Convert a document to PDF from this menu, with or without a profile.")
    print(f"  Accepts: {', '.join(SUPPORTED_SUFFIXES)}")
    print("")
    print("Documentation")
    print(f"  {_hyperlink('Sweepy documentation', DOCS_URL)}")
    print(f"  {_hyperlink('Sweepy README', README_URL)}")


_HELP_SUBMENU_CHOICES = [
    "Command flags",
    "Job engines",
    "Keyboard controls",
    "Documentation & links",
    "Bonus tools",
    "Recent logs",
]


def _print_keyboard_help() -> None:
    print("\nKeyboard controls")
    print("  Esc             Go back one level")
    print("  Ctrl+C          Quit Sweepy")
    print("  Enter or Tab    Accept the current value and advance")
    print("  Arrow keys      Move between tiles and choices")


def _show_help_menu() -> None:
    """Open a dedicated help submenu while preserving the direct help output fallback."""
    _print_nav_help()
    while True:
        action = _menu("Which help section do you want to view?", _HELP_SUBMENU_CHOICES)
        if action is None:
            return
        if action == "Command flags":
            print("\nCommand flags")
            for flag, description in _COMMAND_HELP:
                print(f"  {flag:<32}{description}")
            continue
        if action == "Keyboard controls":
            _print_keyboard_help()
            continue
        if action == "Job engines":
            print("\nJob engines")
            print(status_table())
            print("\nWhat each engine scrapes")
            print(scrapes_table())
            print("\n  Sweepy downloads an engine only after you confirm.")
            print("  Choose 'Download job engines' in the toolbox to install or inspect one.")
            print("  openroles needs company slugs; apify needs APIFY_TOKEN; hirehunt has no proxies.")
            print("  A failing engine is skipped after 5 consecutive failures for 30 seconds.")
            continue
        if action == "Documentation & links":
            print("\nDocumentation")
            print(f"  {_hyperlink('Sweepy documentation', DOCS_URL)}")
            print(f"  {_hyperlink('Sweepy README', README_URL)}")
            continue
        if action == "Bonus tools":
            print("\nBonus tools")
            print("  Convert a document to PDF from this menu, with or without a profile.")
            print(f"  Accepts: {', '.join(SUPPORTED_SUFFIXES)}")
            continue
        if action == "Recent logs":
            _show_recent_logs()


def _ask(question):
    """Add consistent wizard-level navigation keys to a questionary prompt."""
    bindings = KeyBindings()

    @bindings.add(Keys.Escape)
    def go_back(event):
        event.app.exit(exception=_GoBack())

    @bindings.add(Keys.Tab, eager=True)
    def advance_field(event):
        event.app.key_processor.feed(KeyPress(Keys.ControlM))

    question.application.key_bindings = merge_key_bindings(
        [question.application.key_bindings, bindings]
    )
    return question.unsafe_ask()


def _menu(message: str, choices: List[str]) -> Optional[str]:
    """Show a submenu whose first entry goes back one level.

    Returns ``None`` when the user picks Back or presses Esc, so every caller can
    treat "go up" the same way.
    """
    try:
        choice = _ask(_select(message, [BACK_LABEL, *choices]))
    except _GoBack:
        return None
    return None if choice == BACK_LABEL else choice


def _run_action(action: Callable[[], None]) -> None:
    """Run a menu action whose internal prompts may be backed out of with Esc."""
    try:
        action()
    except _GoBack:
        return


def _edit_with_back(editor, profile_data: Dict) -> bool:
    """Run a profile editor and report whether the profile actually changed.

    Esc inside an editor returns to the menu that launched it. Values already
    accepted before the Esc still count, so the exit prompt can offer to save.
    """
    before = copy.deepcopy(profile_data)
    try:
        changed = editor(profile_data)
    except _GoBack:
        changed = False
    return bool(changed) or profile_data != before


def _show_recent_logs() -> None:
    """Print the most recent debug-log lines so users can inspect an in-progress sweep."""
    lines = recent_log_lines(None, lines=50)
    if not lines:
        log.info("No debug logs found. Run Sweepy with --debug to enable logging.")
        return
    print("".join(lines), end="")


try:
    from reportlab.lib.colors import getAllNamedColors as _named_colors

    _COLOR_NAMES = set(_named_colors())
except Exception:  # pragma: no cover - reportlab is a core dependency
    _COLOR_NAMES = {
        "black", "white", "red", "green", "blue", "navy", "gray", "grey",
        "purple", "orange", "yellow", "teal", "maroon", "olive", "silver",
        "aqua", "fuchsia", "lime", "brown", "cyan", "magenta", "gold",
    }

_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _parse_salary(text: str) -> Optional[int]:
    """Parse a salary string like '65000', '65,000', '$65,000', or '65k'. Returns None on failure."""
    s = text.strip().lower().replace("$", "").replace(",", "")
    if not s:
        return 0
    multiplier = 1
    if s.endswith("k"):
        s = s[:-1].strip()
        multiplier = 1000
    try:
        value = int(float(s) * multiplier)
    except (OverflowError, ValueError):
        return None
    if value < 0:
        return None
    return value


def is_valid_color(value: str) -> bool:
    """Return True when ``value`` is a #RGB/#RRGGBB hex code or a known color name."""
    v = (value or "").strip()
    if not v:
        return False
    if _HEX_COLOR_RE.match(v):
        return True
    return v.lower() in _COLOR_NAMES


def _ask_color(track_name: str) -> str:
    while True:
        value = (
            _ask(
                questionary.text(
                    f"Track color (hex code or color name, e.g. #1D4ED8 or navy) for {track_name}:"
                )
            )
            or "#1D4ED8"
        ).strip()
        if is_valid_color(value):
            return value
        log.warning(
            "Invalid color %r. Enter a valid hex code (#RGB or #RRGGBB) or a color name.",
            value,
        )


class _Step:
    """One wizard question: a stable key, a human label, and the ask callable."""

    def __init__(self, key: str, label: str, ask: Callable):
        self.key = key
        self.label = label
        self.ask = ask


def _text_default(current: Any) -> str:
    """Seed a text prompt with the value already on the profile."""
    return "" if current is None else str(current)


def _confirm_default(current: Any) -> bool:
    """Seed a confirm prompt with the value already on the profile."""
    return bool(current) if current is not None else False


def _resume_path_hint() -> str:
    """Return an OS-specific shortcut for copying a file's full path."""
    if sys.platform.startswith("win"):
        return (
            "  Hint: In File Explorer, select the file and press Ctrl+Shift+C "
            "(Windows 11); on older Windows, Shift+right-click and pick Copy as path."
        )
    if sys.platform == "darwin":
        return (
            "  Hint: In Finder, select the file and press Option+Command+C to copy its path."
        )
    return (
        "  Hint: In your file manager, select the file and copy its path "
        "(Ctrl+Shift+C in most file managers)."
    )


def _ask_name(current=None):
    return _ask(questionary.text("What is your name?", default=_text_default(current)))


def _ask_titles(current=None):
    raw = _ask(
        questionary.text(
            "What job titles are you looking for?\n  (Separate multiple titles with a comma)",
            default=", ".join(current) if current else "",
        )
    )
    return [t.strip() for t in (raw or "").split(",") if t.strip()]


def _ask_location(current=None):
    return _ask(
        questionary.text(
            "Where do you want to work? (City, State):", default=_text_default(current)
        )
    )


def _ask_remote_only(current=None):
    return _ask(
        questionary.confirm(
            "Do you want to see remote-only roles?", default=_confirm_default(current)
        )
    )


def _ask_include_hybrid(current=None):
    return _ask(
        questionary.confirm(
            "Do you want to include hybrid roles?", default=_confirm_default(current)
        )
    )


def _ask_resume_path(current=None):
    path = _ask(
        questionary.text(
            f"What is the path to your resume PDF?\n{_resume_path_hint()}",
            default=_text_default(current),
        )
    )
    suffix = os.path.splitext((path or "").strip().strip('"'))[1].lower()
    if suffix in CONVERTIBLE_SUFFIXES:
        convert = _ask(questionary.confirm("Convert this file to PDF?"))
        if convert:
            out = _ask(
                questionary.text(
                    "Output PDF path (leave blank to save next to the file):"
                )
            )
            try:
                return convert_to_pdf(path, out or None)
            except (FileNotFoundError, ValueError, RuntimeError) as exc:
                log.warning("Could not convert the file: %s", exc)
    return path


def _ask_convert_document() -> None:
    """Convert any supported document to PDF, retrying until it works or the user cancels."""
    supported = ", ".join(SUPPORTED_SUFFIXES)
    while True:
        source = (
            _ask(
                questionary.text(
                    f"File to convert ({supported}; leave blank to cancel):"
                )
            )
            or ""
        ).strip().strip('"')
        if not source:
            log.warning("No file provided.")
            return
        out = (
            _ask(
                questionary.text(
                    "Output PDF path (leave blank to save next to the file):"
                )
            )
            or ""
        ).strip().strip('"') or None
        try:
            pdf = convert_to_pdf(source, out)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            log.warning("Could not convert the file: %s", exc)
            continue
        print(f"PDF saved: {pdf}")
        return


def _ask_min_salary(current=None):
    default = str(current) if current else ""
    while True:
        raw = _ask(
            questionary.text(
                "What is your minimum target salary? (Leave blank to skip):", default=default
            )
        )
        parsed = _parse_salary(raw or "")
        if parsed is not None:
            return parsed
        log.warning("Could not parse salary %r. Enter a number like 65000, 65,000, or 65k.", raw)


def _ask_platforms(current=None):
    selected = set(current) if current is not None else {
        "greenhouse", "ashby", "lever", "workable"
    }
    return _ask(
        questionary.checkbox(
            "Which platforms do you want to search?",
            choices=[
                questionary.Choice("Greenhouse", value="greenhouse", checked="greenhouse" in selected),
                questionary.Choice("Ashby", value="ashby", checked="ashby" in selected),
                questionary.Choice("Lever", value="lever", checked="lever" in selected),
                questionary.Choice("Workable", value="workable", checked="workable" in selected),
                questionary.Choice(
                    "Aggregator feeds (Remotive, Adzuna)",
                    value="aggregators",
                    checked="aggregators" in selected,
                ),
            ],
        )
    ) or []


def _ask_custom_platforms(current=None):
    existing = list(current or [])
    if existing:
        keep = _ask(
            questionary.confirm(
                f"Keep your {len(existing)} custom platform(s)?", default=True
            )
        )
        if keep:
            return existing
    add_custom = _ask(
        questionary.confirm(
            "Do you want to add custom platforms or ATS domains?",
            default=_confirm_default(current),
        )
    )
    custom_platforms = []
    if add_custom:
        custom_input = _ask(
            questionary.text(
                "Enter custom platform names and domains (format: Name:domain.com, comma-separated):\n  e.g. SmartRecruiters:smartrecruiters.com, Breezy HR:breezy.hr"
            )
        )
        if custom_input:
            for item in custom_input.split(","):
                item = item.strip()
                if ":" in item:
                    c_name, c_domain = item.split(":", 1)
                    custom_platforms.append({
                        "name": c_name.strip(),
                        "domain": c_domain.strip().lower(),
                        "enabled": True,
                    })
    return custom_platforms


def _ask_skills(current=None):
    raw = _ask(
        questionary.text(
            "Enter must-have skills or keywords to prioritize (comma-separated, leave blank to extract from resume):",
            default=", ".join(current) if current else "",
        )
    )
    return [s.strip() for s in (raw or "").split(",") if s.strip()]


def _ask_formats(current=None):
    selected = set(current) if current is not None else {"pdf", "csv"}
    while True:
        formats = _ask(
            questionary.checkbox(
                "What export formats do you want?",
                choices=[
                    questionary.Choice("PDF Report", value="pdf", checked="pdf" in selected),
                    questionary.Choice("CSV Spreadsheet", value="csv", checked="csv" in selected),
                    questionary.Choice("JSON Data", value="json", checked="json" in selected),
                ],
            )
        )
        if formats:
            return formats
        log.warning("Select at least one export format.")


def _ask_tracks(current=None):
    existing = list(current or [])
    if existing:
        keep = _ask(
            questionary.confirm(f"Keep your {len(existing)} resume track(s)?", default=True)
        )
        if keep:
            return existing
    tracks = []
    add_tracks = _ask(
        questionary.confirm(
            "Do you want to configure multiple resume tracks (e.g. Tech Writer vs UX Writer)?",
            default=_confirm_default(current),
        )
    )
    if add_tracks:
        while True:
            track_name = _ask(questionary.text("Track name (leave blank to finish):"))
            if not track_name or not track_name.strip():
                break
            track_color = _ask_color(track_name.strip())
            resume_path = _ask(
                questionary.text(
                    "Resume PDF path for this track (leave blank to use the main resume):\n"
                    f"{_resume_path_hint()}"
                )
            )
            keywords_str = _ask(
                questionary.text(
                    f"Routing keywords for {track_name.strip()} (comma-separated):"
                )
            )
            tracks.append({
                "name": track_name.strip(),
                "color": track_color,
                "path": (resume_path or "").strip(),
                "route_keywords": [k.strip() for k in (keywords_str or "").split(",") if k.strip()],
            })
    return tracks


def _ask_debug(current=None):
    return _ask(
        questionary.confirm(
            "Enable debug logging? (Logs are saved under logs/ in the application directory):",
            default=_confirm_default(current),
        )
    )


_JOBDROP_BOARDS = [
    "linkedin",
    "indeed",
    "glassdoor",
    "google",
    "zip_recruiter",
    "wellfound",
    "hiring_cafe",
    "trueup",
    "remoteok",
    "weworkremotely",
    "builtin",
    "dice",
]


def _engine_status_label(name: str) -> str:
    status = engine_status(name)
    if status["core"]:
        return "built in"
    return "installed" if status["installed"] else "download"


def _engine_choice_label(name: str) -> str:
    info = ENGINE_CATALOG[name]
    adapter = ADAPTERS[name]
    caps = [
        label
        for flag, label in (
            ("supports_proxies", "proxies"),
            ("supports_user_agent", "User-Agent"),
            ("supports_description_toggle", "descriptions"),
        )
        if getattr(adapter, flag)
    ]
    capability_text = ", ".join(caps) or "basic"
    return f"{name:<9} [{_engine_status_label(name):<9}] {info.blurb} ({capability_text})"


def _engine_details(name: str) -> str:
    info = ENGINE_CATALOG[name]
    status = engine_status(name)
    lines = [
        f"{name} - {info.blurb}",
        f"  Status:     {'installed' if status['installed'] else 'not installed'}",
        f"  Package:    {info.package or 'built in'}",
        f"  Region:     {info.regions or 'global'}",
        f"  Scrapes:    {', '.join(info.scrapes)}",
    ]
    if info.needs:
        lines.append(f"  Requires:   {', '.join(info.needs)}")
    if info.notes:
        lines.append(f"  Note:       {info.notes}")
    return "\n".join(lines)


def _ensure_engine_available(name: str) -> bool:
    """Offer to install a missing engine before its prompts run."""
    if engine_status(name)["installed"]:
        return True
    download = _ask(
        questionary.confirm(
            f"{name} is not installed. Download it now with pip?", default=True
        )
    )
    if not download:
        log.info("Skipped %s. Install it later with: %s", name, install_command([name]))
        return False

    result = install_engines([name], echo=print).get(name, {})
    if not result.get("installed"):
        log.warning("Could not install %s: %s", name, result.get("detail", "unknown error"))
        log.info("Retry with: %s", result.get("command") or install_command([name]))
        return False
    log.info("%s installed.", name)
    return True


def _ask_proxies(current=None) -> List[str]:
    """Collect proxies from a file or an inline entry without echoing credentials."""
    existing = list(current or [])
    if existing and _ask(
        questionary.confirm(f"Keep your {len(existing)} configured proxy target(s)?", default=True)
    ):
        return existing
    if not _ask(questionary.confirm("Route requests through proxies?", default=False)):
        return []

    if _ask(questionary.confirm("Load proxies from a file?", default=True)):
        path = (_ask(questionary.text("Proxy file path:", default="./proxies.txt")) or "").strip()
        if not path:
            return []
        try:
            with open(os.path.expanduser(path), encoding="utf-8") as handle:
                proxies = [line.strip() for line in handle if line.strip()]
        except OSError as exc:
            log.warning("Could not read the proxy file: %s", exc)
            return []
        log.info("Loaded %d proxy target(s). Contents stay hidden.", len(proxies))
        return proxies

    host = (_ask(questionary.text("Proxy host:port:")) or "").strip()
    if not host:
        return []
    if "@" not in host:
        user = (_ask(questionary.text("Proxy username (leave blank if none):")) or "").strip()
        if user:
            password = _ask(questionary.password("Proxy password:")) or ""
            host = f"{user}:{password}@{host}"
    return [host]


def _ask_jobspy(current=None) -> dict:
    current = current or {}
    selected = set(current.get("sites") or DEFAULT_JOBSPY_SITES)
    sites = _ask(
        questionary.checkbox(
            "JobSpy boards:",
            choices=[
                questionary.Choice(board.title(), value=board, checked=board in selected)
                for board in DEFAULT_JOBSPY_SITES
            ],
        )
    ) or list(DEFAULT_JOBSPY_SITES)
    descriptions = _ask(
        questionary.confirm(
            "Fetch full descriptions? (Slower, but scores need the posting text)",
            default=bool(current.get("fetch_descriptions", True)),
        )
    )
    user_agent = (
        _ask(
            questionary.text(
                "User-Agent override (leave blank for the built-in Chrome string):",
                default=str(current.get("user_agent") or ""),
            )
        )
        or ""
    ).strip()
    return {
        "sites": sites,
        "fetch_descriptions": bool(descriptions),
        "proxies": _ask_proxies(current.get("proxies")),
        "user_agent": user_agent or None,
        "results_per_title": current.get("results_per_title", 25),
    }


def _ask_hirehunt(current=None) -> dict:
    current = current or {}
    selected = set(current.get("sources") or DEFAULT_HIREHUNT_SOURCES)
    sources = _ask(
        questionary.checkbox(
            "HireHunt sources:",
            choices=[
                questionary.Choice(source.replace("_", " ").title(), value=source, checked=source in selected)
                for source in DEFAULT_HIREHUNT_SOURCES
            ],
        )
    ) or list(DEFAULT_HIREHUNT_SOURCES)
    log.info("HireHunt has no proxy hook, so proxy settings stay disabled.")
    return {"sources": sources}


def _ask_jobdrop(current=None) -> dict:
    current = current or {}
    selected = set(current.get("sites") or DEFAULT_JOBDROP_SITES)
    sites = _ask(
        questionary.checkbox(
            "jobdrop boards:",
            choices=[
                questionary.Choice(board.replace("_", " ").title(), value=board, checked=board in selected)
                for board in _JOBDROP_BOARDS
            ],
        )
    ) or list(DEFAULT_JOBDROP_SITES)
    headless = _ask(
        questionary.confirm("Run browser-backed boards headless?", default=bool(current.get("headless", True)))
    )
    descriptions = _ask(
        questionary.confirm(
            "Fetch full descriptions?",
            default=bool(current.get("fetch_descriptions", True)),
        )
    )
    return {
        "sites": sites,
        "headless": bool(headless),
        "fetch_descriptions": bool(descriptions),
        "proxies": _ask_proxies(current.get("proxies")),
    }


def _ask_openroles(current=None) -> dict:
    current = current or {}
    selected = set(current.get("ats") or DEFAULT_OPENROLES_ATS)
    ats = _ask(
        questionary.checkbox(
            "ATS platforms:",
            choices=[
                questionary.Choice(name.title(), value=name, checked=name in selected)
                for name in DEFAULT_OPENROLES_ATS
            ],
        )
    ) or list(DEFAULT_OPENROLES_ATS)

    companies: List[str] = []
    while not companies:
        raw = _ask(
            questionary.text(
                "Company slugs, comma-separated (example: figma, stripe, notion):",
                default=", ".join(current.get("companies") or []),
            )
        ) or ""
        companies = [company.strip() for company in raw.split(",") if company.strip()]
        if not companies:
            log.warning("openroles reads boards you name, so at least one company slug is required.")
    return {"ats": ats, "companies": companies}


def _ask_apify(current=None) -> Optional[dict]:
    current = current or {}
    token = os.environ.get("APIFY_TOKEN") or current.get("token")
    if not token:
        log.warning("APIFY_TOKEN is not set. Add it to the environment, then enable apify again.")
        return None
    actor = (
        _ask(
            questionary.text(
                "Apify actor id:",
                default=str(current.get("actor") or DEFAULT_APIFY_ACTOR),
            )
        )
        or DEFAULT_APIFY_ACTOR
    ).strip()
    return {"token": None, "actor": actor or DEFAULT_APIFY_ACTOR}


_ENGINE_PROMPTS = {
    "jobspy": _ask_jobspy,
    "hirehunt": _ask_hirehunt,
    "jobdrop": _ask_jobdrop,
    "openroles": _ask_openroles,
    "apify": _ask_apify,
}


def _ask_engines(current: Optional[dict] = None) -> Optional[dict]:
    """Pick engines, download any that are missing, then collect their settings.

    Returns ``None`` when the user backs out, so the caller keeps the previous config.
    """
    current = current or {}
    try:
        enabled = list(current.get("enabled") or ["jobspy", "ats"])
        selected = _ask(
            questionary.checkbox(
                "Which job engines should Sweepy use? Missing engines download on selection.",
                choices=[
                    questionary.Choice(
                        _engine_choice_label(name), value=name, checked=name in enabled
                    )
                    for name in ENGINE_CATALOG
                ],
            )
        )
        if not selected:
            log.warning("Keep at least one engine, otherwise a sweep finds nothing.")

        keep: List[str] = []
        config: dict = {"enabled": keep}
        for name in selected or []:
            if not _ensure_engine_available(name):
                continue
            prompt = _ENGINE_PROMPTS.get(name)
            if prompt is None:
                keep.append(name)
                continue
            try:
                engine_config = prompt(dict(current.get(name) or {}))
            except ValueError as exc:
                log.warning("%s settings rejected: %s", name, exc)
                continue
            if engine_config is None:
                log.warning("%s stays disabled.", name)
                continue
            keep.append(name)
            config[name] = engine_config
    except _GoBack:
        return None

    errors = validate_sources({name: config.get(name, {}) for name in keep})
    for error in errors:
        log.warning("Configuration needs attention: %s", error)
    return config


def _ask_orchestrator(current=None) -> Optional[dict]:
    """Collect timeout, cache, and circuit-breaker settings. Returns None on Back."""
    current = current or {}
    cache = dict(current.get("cache") or {})
    breaker = dict(current.get("circuit_breaker") or {})

    def _ask_int(prompt: str, default: int) -> int:
        raw = _ask(questionary.text(prompt, default=str(default)))
        return _parse_int(raw or "") or default

    try:
        timeout = _ask_int(
            "Per-source timeout in seconds:", int(current.get("timeout_per_source_seconds", 180))
        )
        cache_enabled = _ask(
            questionary.confirm(
                "Cache discovery results between runs?", default=bool(cache.get("enabled", True))
            )
        )
        ttl = _ask_int("Cache lifetime in seconds:", int(cache.get("ttl_seconds", 3600)))
        threshold = _ask_int(
            "Skip an engine after this many consecutive failures:",
            int(breaker.get("failure_threshold", 5)),
        )
        cooldown = _ask_int(
            "Cooldown before retrying a skipped engine (seconds):",
            int(breaker.get("cooldown_seconds", 30)),
        )
    except _GoBack:
        return None
    return {
        "timeout_per_source_seconds": max(1, timeout),
        "cache": {"enabled": bool(cache_enabled), "ttl_seconds": max(0, ttl)},
        "circuit_breaker": {
            "failure_threshold": max(1, threshold),
            "cooldown_seconds": max(1, cooldown),
        },
    }


def _manage_engines() -> None:
    """Show what each engine scrapes and install missing libraries on request."""

    def _report(results: dict) -> None:
        for name, result in results.items():
            if result.get("installed"):
                log.info("%s installed.", name)
            else:
                log.warning("Could not install %s: %s", name, result.get("detail"))
                log.info("Retry with: %s", result.get("command") or install_command([name]))

    def apply_choice(action: str) -> None:
        if action == "Install all missing engines":
            targets = missing_engines()
            if not targets:
                log.info("Every engine is already installed.")
                return
            if not _ask(
                questionary.confirm(
                    f"Download {len(targets)} engine(s): {', '.join(targets)}?", default=True
                )
            ):
                return
            _report(install_engines(targets, echo=print))
            return

        if action == "Install one engine":
            targets = missing_engines()
            if not targets:
                log.info("Every engine is already installed.")
                return
            name = _menu("Which engine do you want to download?", targets)
            if name is None:
                return
            if not _ask(questionary.confirm(f"Download {name} with pip now?", default=True)):
                log.info("Run this later: %s", install_command([name]))
                return
            _report(install_engines([name], echo=print))
            return

        if action == "Show engine details":
            name = _menu("Which engine?", list(ENGINE_CATALOG))
            if name is None:
                return
            print("")
            print(_engine_details(name))

    while True:
        print("\nJob engines")
        print(status_table())
        print("\nWhat each engine scrapes")
        print(scrapes_table())
        print("")
        action = _menu(
            "Engine downloads:",
            [
                "Install all missing engines",
                "Install one engine",
                "Show engine details",
            ],
        )
        if action is None:
            return
        try:
            apply_choice(action)
        except _GoBack:
            continue


def _edit_sources(profile_data: Dict) -> bool:
    """Edit engines, settings, and downloads without running the whole questionnaire."""
    changed = False
    while True:
        runtime = normalize_sources(profile_data)
        log.info("  Engines: %s", ", ".join(runtime["enabled"]) or "(none)")
        action = _menu(
            "Job engines",
            [
                "Choose engines and settings",
                "Download a job engine",
                "Show what each engine scrapes",
            ],
        )
        if action is None:
            return changed
        if action == "Download a job engine":
            _manage_engines()
            continue
        if action == "Show what each engine scrapes":
            for name in ENGINE_CATALOG:
                print(_engine_details(name))
                print("")
            continue

        current = _answers_from_profile(profile_data).get("sources") or {}
        answers = _ask_engines(current)
        if answers is None:
            continue
        _apply_sources(profile_data, answers)
        changed = True
        log.info("Engines updated: %s", ", ".join(answers.get("enabled") or []) or "(none)")


def _apply_sources(profile_data: Dict, answers: Optional[dict]) -> None:
    if not answers:
        return
    sources = dict(profile_data.get("sources") or {})
    sources["enabled"] = list(answers.get("enabled") or [])
    for name, config in answers.items():
        if name == "enabled":
            continue
        sources[name] = config
    profile_data["sources"] = sources


def _apply_orchestrator(profile_data: Dict, answers: Optional[dict]) -> None:
    if not answers:
        return
    profile_data["cache"] = dict(answers.get("cache") or {})
    profile_data["orchestrator"] = {
        "timeout_per_source_seconds": answers.get("timeout_per_source_seconds", 180),
        "circuit_breaker": dict(answers.get("circuit_breaker") or {}),
    }


def _build_steps():
    return [
        _Step("name", "Your name", _ask_name),
        _Step("titles", "Job titles", _ask_titles),
        _Step("location", "Location", _ask_location),
        _Step("remote_only", "Remote-only roles", _ask_remote_only),
        _Step("include_hybrid", "Hybrid roles", _ask_include_hybrid),
        _Step("resume_path", "Resume path", _ask_resume_path),
        _Step("min_salary", "Minimum salary", _ask_min_salary),
        _Step("platforms", "Platforms", _ask_platforms),
        _Step("custom_platforms", "Custom platforms", _ask_custom_platforms),
        _Step("must_have_skills", "Must-have skills", _ask_skills),
        _Step("formats", "Export formats", _ask_formats),
        _Step("tracks", "Resume tracks", _ask_tracks),
        _Step("debug", "Debug logging", _ask_debug),
    ]


def _collect(steps, seed=None):
    """Ask every step in order; Esc walks back one question, then out of the flow."""
    answers = {}
    index = 0
    while index < len(steps):
        step = steps[index]
        current = (seed or {}).get(step.key)
        if current is None:
            current = answers.get(step.key)
        try:
            answers[step.key] = step.ask(current)
        except _GoBack:
            if index == 0:
                raise
            index -= 1
            continue
        index += 1
    return answers


def _format_answer(step, value):
    if step.key == "platforms":
        return ", ".join(value) if value else "(none)"
    if step.key == "custom_platforms":
        return ", ".join(c["name"] for c in value) if value else "(none)"
    if step.key == "tracks":
        return ", ".join(t["name"] for t in value) if value else "(none)"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if value in (None, ""):
        return "(blank)"
    return str(value)


def _print_summary(answers, steps):
    log.info("──────────────────────────────────────────────────")
    log.info("Review your answers before submitting:")
    for step in steps:
        log.info("  %s: %s", step.label, _format_answer(step, answers.get(step.key)))
    log.info("  Job engines: %s", _format_engines(answers.get("sources")))
    log.info("  Engine performance: %s", _format_orchestrator(answers.get("orchestrator")))
    log.info("──────────────────────────────────────────────────")


def _format_engines(value) -> str:
    enabled = (value or {}).get("enabled") or []
    return ", ".join(enabled) if enabled else "(defaults: jobspy, ats)"


def _format_orchestrator(value) -> str:
    if not value:
        return "(defaults: 180s timeout, cache on)"
    cache = value.get("cache") or {}
    state = "on" if cache.get("enabled", True) else "off"
    return (
        f"timeout {value.get('timeout_per_source_seconds', 180)}s, "
        f"cache {state} ({cache.get('ttl_seconds', 3600)}s)"
    )


_PLATFORM_KEYS = ("greenhouse", "ashby", "lever", "workable", "aggregators")


def _parse_int(text: str) -> Optional[int]:
    """Parse a whole number such as '24' or '1,024'. Returns None on failure."""
    s = (text or "").strip().replace(",", "")
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _parse_float(text: str) -> Optional[float]:
    """Parse a decimal such as '1.5' or '2'. Returns None on failure."""
    s = (text or "").strip()
    if not s:
        return None
    try:
        value = float(s)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _answers_from_profile(profile_data: Dict) -> Dict:
    """Flatten a profile dict into the wizard's answer keys."""
    search = profile_data.get("search") or {}
    resume = profile_data.get("resume") or {}
    platforms = profile_data.get("platforms") or {}
    export = profile_data.get("export") or {}
    formats = [f.strip() for f in str(export.get("format", "pdf,csv")).split(",") if f.strip()]
    enabled = [key for key in _PLATFORM_KEYS if platforms.get(key)]
    runtime = normalize_sources(profile_data)
    engine_answers = {"enabled": list(runtime["enabled"])}
    for name in ("jobspy", "hirehunt", "openroles", "jobdrop", "apify"):
        engine_answers[name] = copy.deepcopy(runtime["engines"][name])
    return {
        "name": profile_data.get("name", ""),
        "titles": list(search.get("titles") or []),
        "location": search.get("location", ""),
        "remote_only": bool(search.get("remote_only")),
        "include_hybrid": bool(search.get("include_hybrid", True)),
        "resume_path": resume.get("path", ""),
        "min_salary": search.get("min_salary", 0),
        "platforms": enabled,
        "custom_platforms": [dict(c) for c in (platforms.get("custom") or [])],
        "sources": engine_answers,
        "orchestrator": {
            "timeout_per_source_seconds": runtime["orchestrator"]["timeout_per_source_seconds"],
            "cache": dict(runtime["cache"]),
            "circuit_breaker": dict(runtime["orchestrator"]["circuit_breaker"]),
        },
        "must_have_skills": list(resume.get("must_have_skills") or []),
        "formats": formats,
        "tracks": [dict(t) for t in (resume.get("tracks") or [])],
        "debug": bool(profile_data.get("debug")),
    }


def _merge_answers(profile_data: Dict, answers: Dict) -> Dict:
    """Write the wizard's answers back onto a profile, preserving unknown keys.

    Editing an existing profile must not drop sections the wizard has no question
    for, such as ``sources``, ``resume.synonyms``, or ``report.destinations``.
    """
    merged = copy.deepcopy(profile_data)

    merged["name"] = answers.get("name") or "Job Seeker"

    search = dict(merged.get("search") or {})
    search["titles"] = answers.get("titles") or ["Paralegal"]
    search["location"] = answers.get("location") or "New York, NY"
    search["remote_only"] = bool(answers.get("remote_only"))
    search["include_hybrid"] = bool(answers.get("include_hybrid"))
    search["min_salary"] = answers.get("min_salary", 0)
    merged["search"] = search

    resume = dict(merged.get("resume") or {})
    resume["path"] = (answers.get("resume_path") or "").strip().strip('"').replace("\\", "/")
    resume["must_have_skills"] = answers.get("must_have_skills") or []
    resume.setdefault("keywords_weight", 1.5)
    tracks = answers.get("tracks") or []
    if tracks:
        resume["tracks"] = tracks
    elif merged.get("resume", {}).get("tracks"):
        resume.pop("tracks", None)
    merged["resume"] = resume

    platforms = dict(merged.get("platforms") or {})
    selected = answers.get("platforms") or []
    for key in _PLATFORM_KEYS:
        platforms[key] = key in selected
    custom = answers.get("custom_platforms") or []
    if custom:
        platforms["custom"] = custom
    elif (merged.get("platforms") or {}).get("custom"):
        platforms.pop("custom", None)
    merged["platforms"] = platforms

    if answers.get("sources_dirty"):
        _apply_sources(merged, answers.get("sources"))
    if answers.get("orchestrator_dirty"):
        _apply_orchestrator(merged, answers.get("orchestrator"))

    report = dict(merged.get("report") or {})
    report.setdefault("style", "cards")
    report.setdefault("cards_per_page", 4)
    report.setdefault("max_cards", 24)
    merged["report"] = report

    export = dict(merged.get("export") or {})
    export["format"] = ",".join(answers.get("formats") or ["pdf", "csv"])
    export.setdefault("output_dir", "results")
    merged["export"] = export

    merged["debug"] = bool(answers.get("debug"))
    return merged


def _build_profile(answers):
    return _merge_answers({}, answers)


def _profile_path(profile_data):
    titles = profile_data["search"]["titles"]
    first_title_slug = re.sub(r'[^a-zA-Z0-9]+', '_', (titles[0] if titles else "custom")).strip('_').lower()
    safe_name = re.sub(r'[^a-zA-Z0-9]+', '_', profile_data["name"]).strip('_').lower()
    return f"profiles/{safe_name}_{first_title_slug}.yaml"


MENU_RUN = "Run a sweep"
MENU_CREATE = "Create a new profile"
MENU_LOAD = "Load an existing profile"
MENU_EDIT = "Edit an existing profile"
MENU_DEBUG = "Toggle debug logging"
MENU_SCALING = "Adjust scoring and scaling"
MENU_AGGREGATORS = "Add or edit aggregators"
MENU_SOURCES = "Manage job engines"
MENU_ENGINES = "Download job engines"
MENU_HELP = "Show help"
MENU_LOGS = "Show recent logs"
MENU_CONVERT = "Convert a document to PDF (bonus)"
MENU_UPDATE = "Update Sweepy"
MENU_EXIT = "Exit"
MENU_TOOLBOX = "Open the toolbox"

_MENU_TILES = [
    ("01", "LAUNCH SWEEP", "Search enabled sources", MENU_RUN),
    ("02", "BUILD PROFILE", "Set up a new job search", MENU_CREATE),
    ("03", "LOAD PROFILE", "Choose a saved job search", MENU_LOAD),
    ("04", "TUNE SEARCH", "Scoring and reports", MENU_SCALING),
    ("05", "OPEN TOOLBOX", "Edits, tools and settings", MENU_TOOLBOX),
    ("06", "EXIT SWEEPY", "Save changes and close", MENU_EXIT),
]

_SCALING_CHOICES = [
    "Keyword weight (resume.keywords_weight)",
    "Maximum cards (report.max_cards)",
    "Cards per page (report.cards_per_page)",
    "Report style (report.style)",
]

_AGGREGATOR_CHOICES = [
    "Toggle aggregator feeds",
    "Add a custom aggregator",
    "Edit a custom aggregator",
    "Remove a custom aggregator",
]


def _toolbox_choices() -> List[str]:
    return [
        MENU_EDIT,
        MENU_SOURCES,
        MENU_ENGINES,
        MENU_AGGREGATORS,
        MENU_DEBUG,
        MENU_HELP,
        MENU_LOGS,
        MENU_CONVERT,
        MENU_UPDATE,
        MENU_EXIT,
    ]


def record_last_profile(profile_path: str) -> None:
    """Remember ``profile_path`` so ``python swee.py --run`` can reuse it."""
    if not profile_path:
        return
    try:
        os.makedirs(os.path.dirname(_LAST_PROFILE_FILE) or "profiles", exist_ok=True)
        with open(_LAST_PROFILE_FILE, "w", encoding="utf-8") as f:
            f.write(os.path.abspath(profile_path))
    except OSError as exc:
        log.warning("Could not record the last profile: %s", exc)


def last_profile_path() -> Optional[str]:
    """Return the last saved profile, falling back to the newest one in ``profiles/``."""
    try:
        with open(_LAST_PROFILE_FILE, encoding="utf-8") as f:
            recorded = f.read().strip()
    except OSError:
        recorded = ""

    if recorded and os.path.exists(recorded):
        return recorded

    candidates = _list_profiles()
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def _list_profiles(directory: str = "profiles") -> List[str]:
    """Return the profile YAML paths under ``directory``, sorted for stable menus."""
    if not os.path.isdir(directory):
        return []
    return sorted(
        os.path.join(directory, name).replace("\\", "/")
        for name in os.listdir(directory)
        if name.lower().endswith((".yaml", ".yml"))
    )


def _custom_label(entry: Dict) -> str:
    return f"{entry.get('name', '?')} ({entry.get('domain', '?')})"


def _require_profile(profile_data: Optional[Dict]) -> bool:
    if profile_data:
        return True
    log.warning("Create or edit a profile first.")
    return False


def _run_loaded_profile(
    profile_data: Optional[Dict],
    working_path: Optional[str],
    run_sweep: Optional[Callable[[Dict, Optional[str]], None]],
) -> None:
    """Run the sweep from the menu, passing the in-memory profile so unsaved edits count."""
    if not _require_profile(profile_data):
        return
    if run_sweep is None:
        log.warning("Run the sweep from the command line: python swee.py --run")
        return
    run_sweep(profile_data, working_path)


def _review_answers(
    answers: Dict,
    steps,
    reload_answers,
    submit_label: str = "Submit profile",
    defaults: Optional[Dict] = None,
) -> None:
    """Show the answer summary and return once the user submits."""
    defaults = defaults or {}
    while True:
        _print_summary(answers, steps)
        action = _menu(
            "What would you like to do?",
            [
                submit_label,
                "Edit an answer",
                MENU_SOURCES,
                "Adjust engine performance",
                MENU_ENGINES,
                MENU_CONVERT,
                "Show help",
                "Show recent logs",
                "Start over",
            ],
        )
        if action == submit_label:
            return
        if action is None:
            if not steps:
                return
            _reopen_last_step(answers, steps)
            continue
        if action == "Start over":
            try:
                answers.clear()
                answers.update(reload_answers())
            except _GoBack:
                return
            continue
        if action == MENU_ENGINES:
            _run_action(_manage_engines)
            continue
        if action == MENU_SOURCES:
            current = answers.get("sources") or _engine_defaults(defaults)
            edited = _ask_engines(current)
            if edited is not None:
                answers["sources"] = edited
                answers["sources_dirty"] = True
            continue
        if action == "Adjust engine performance":
            current = answers.get("orchestrator") or _orchestrator_defaults(defaults)
            edited = _ask_orchestrator(current)
            if edited is not None:
                answers["orchestrator"] = edited
                answers["orchestrator_dirty"] = True
            continue
        if action == "Show help":
            _run_action(_show_help_menu)
            continue
        if action == "Show recent logs":
            _run_action(_show_recent_logs)
            continue
        if action == MENU_CONVERT:
            _run_action(_ask_convert_document)
            continue

        label = _menu(
            "Which answer do you want to edit?",
            [step.label for step in steps],
        )
        if label is None:
            continue
        step = next(s for s in steps if s.label == label)
        try:
            answers[step.key] = step.ask(answers.get(step.key))
        except _GoBack:
            continue


def _reopen_last_step(answers: Dict, steps) -> None:
    """Back from the review screen reopens the last question instead of losing answers."""
    if not steps:
        return
    step = steps[-1]
    try:
        answers[step.key] = step.ask(answers.get(step.key))
    except _GoBack:
        return


def _engine_defaults(profile_data: Optional[Dict]) -> Dict:
    if not profile_data:
        return {}
    answers = _answers_from_profile(profile_data)
    return answers.get("sources") or {}


def _orchestrator_defaults(profile_data: Optional[Dict]) -> Dict:
    if not profile_data:
        return {}
    answers = _answers_from_profile(profile_data)
    return answers.get("orchestrator") or {}


def _save_profile_flow(profile_data: Dict, source_path: Optional[str] = None) -> Optional[str]:
    """Save the working profile, asking where an edited copy should land."""
    if not source_path:
        return save_profile(profile_data, _profile_path(profile_data))

    try:
        action = _ask(
            _select(
                "How do you want to save this profile?",
                [f"Overwrite {source_path}", "Save as a new file"],
            )
        )
        if action is None:
            return None
        if action.startswith("Overwrite"):
            return save_profile(profile_data, source_path)

        default_path = _profile_path(profile_data)
        raw = _ask(
            questionary.text(
                "Save as (leave blank for the default path):", default=default_path
            )
        )
    except _GoBack:
        return None
    return save_profile(profile_data, (raw or "").strip() or default_path)


def _create_profile_flow() -> Optional[Tuple[str, Dict]]:
    steps = _build_steps()
    try:
        answers = _collect(steps)
        _review_answers(answers, steps, lambda: _collect(steps))
    except _GoBack:
        return None
    profile_data = _build_profile(answers)
    return save_profile(profile_data, _profile_path(profile_data)), profile_data


def _load_profile_flow(profile_path: Optional[str] = None) -> Optional[Tuple[str, Dict]]:
    try:
        if profile_path is not None and not os.path.exists(profile_path):
            log.warning("Profile not found: %s", profile_path)
            profile_path = None

        if profile_path is None:
            choices = _list_profiles()
            if not choices:
                log.warning("No profiles found in profiles/. Create a new profile first.")
                return None
            profile_path = _menu("Which profile do you want to edit?", choices)
            if profile_path is None:
                return None

        profile_data = load_config(profile_path)
        notice = legacy_profile_notice(profile_data)
        if notice:
            log.info(notice)
        steps = _build_steps()
        seed = _answers_from_profile(profile_data)
        answers = dict(seed)
        _review_answers(
            answers,
            steps,
            lambda: dict(seed),
            submit_label="Submit changes",
            defaults=profile_data,
        )
        merged = _merge_answers(profile_data, answers)
    except _GoBack:
        return None
    saved_path = _save_profile_flow(merged, profile_path) or profile_path
    return saved_path, merged


def _load_saved_profile_flow() -> Optional[Tuple[str, Dict]]:
    """Select and activate a saved profile without opening the edit questionnaire."""
    choices = _list_profiles()
    if not choices:
        log.warning("No profiles found in profiles/. Create a new profile first.")
        return None

    profile_path = _menu(
        "Which profile do you want to load?", choices
    )
    if profile_path is None:
        return None

    profile_data = load_config(profile_path)
    record_last_profile(profile_path)
    notice = legacy_profile_notice(profile_data)
    if notice:
        log.info(notice)
    return profile_path, profile_data


def _edit_scaling(profile_data: Dict) -> bool:
    """Adjust the keyword weight and the report scaling options in place."""
    resume = profile_data.setdefault("resume", {})
    report = profile_data.setdefault("report", {})
    changed = False

    def apply_choice(action: str) -> None:
        nonlocal changed
        if action.startswith("Keyword weight"):
            while True:
                raw = _ask(
                    questionary.text(
                        "Keyword weight (0 or higher, e.g. 1.5):",
                        default=str(resume.get("keywords_weight", 1.5)),
                    )
                )
                value = _parse_float(raw)
                if value is not None and value >= 0:
                    resume["keywords_weight"] = value
                    changed = True
                    return
                log.warning("Enter a number 0 or higher, such as 1.5.")
        if action.startswith("Maximum cards"):
            while True:
                raw = _ask(
                    questionary.text(
                        "Maximum cards (0 for unlimited):",
                        default=str(report.get("max_cards", 24)),
                    )
                )
                value = _parse_int(raw)
                if value is not None and value >= 0:
                    report["max_cards"] = value
                    changed = True
                    return
                log.warning("Enter a whole number 0 or higher. 0 means unlimited.")
        if action.startswith("Cards per page"):
            while True:
                raw = _ask(
                    questionary.text(
                        "Cards per page (1 or higher):",
                        default=str(report.get("cards_per_page", 4)),
                    )
                )
                value = _parse_int(raw)
                if value is not None and value >= 1:
                    report["cards_per_page"] = value
                    changed = True
                    return
                log.warning("Enter a whole number 1 or higher.")
        if action.startswith("Report style"):
            style = _ask(
                _select(
                    "Report style:",
                    ["cards", "legacy"],
                    default=str(report.get("style", "cards")),
                )
            )
            if style is not None:
                report["style"] = style
                changed = True

    while True:
        log.info(
            "  Keyword weight %s | Max cards %s | Cards per page %s | Report style %s",
            resume.get("keywords_weight", 1.5),
            report.get("max_cards", 24),
            report.get("cards_per_page", 4),
            report.get("style", "cards"),
        )
        action = _menu(
            "Which scaling setting do you want to change?", _SCALING_CHOICES
        )
        if action is None:
            return changed
        try:
            apply_choice(action)
        except _GoBack:
            continue


def _edit_aggregators(profile_data: Dict) -> bool:
    """Toggle aggregator feeds and manage the custom aggregator list in place."""
    platforms = profile_data.setdefault("platforms", {})
    changed = False

    def apply_choice(action: str) -> None:
        nonlocal changed
        custom = platforms.get("custom") or []

        if action == "Toggle aggregator feeds":
            platforms["aggregators"] = not bool(platforms.get("aggregators"))
            changed = True
            log.info(
                "Aggregator feeds turned %s.",
                "on" if platforms["aggregators"] else "off",
            )
            return

        if action == "Add a custom aggregator":
            name = (_ask(questionary.text("Aggregator name (e.g. SmartRecruiters):")) or "").strip()
            domain = (
                _ask(questionary.text("Aggregator domain (e.g. smartrecruiters.com):")) or ""
            ).strip().lower()
            if not name or not domain:
                log.warning("Both a name and a domain are required.")
                return
            updated = [c for c in custom if c.get("name") != name]
            updated.append({"name": name, "domain": domain, "enabled": True})
            platforms["custom"] = updated
            changed = True
            log.info("Added %s.", name)
            return

        if action == "Edit a custom aggregator":
            if not custom:
                log.warning("No custom aggregators yet. Add one first.")
                return
            label = _ask(
                _select(
                    "Which aggregator do you want to edit?",
                    [_custom_label(c) for c in custom],
                )
            )
            if label is None:
                return
            entry = next((c for c in custom if _custom_label(c) == label), None)
            if entry is None:
                return
            name = (
                _ask(
                    questionary.text(
                        "Aggregator name:", default=str(entry.get("name", ""))
                    )
                )
                or ""
            ).strip()
            domain = (
                _ask(
                    questionary.text(
                        "Aggregator domain:", default=str(entry.get("domain", ""))
                    )
                )
                or ""
            ).strip().lower()
            enabled = _ask(
                questionary.confirm(
                    "Keep this aggregator enabled?", default=bool(entry.get("enabled", True))
                )
            )
            if not name or not domain:
                log.warning("Both a name and a domain are required.")
                return
            entry.update({"name": name, "domain": domain, "enabled": bool(enabled)})
            changed = True
            log.info("Updated %s.", name)
            return

        if action == "Remove a custom aggregator":
            if not custom:
                log.warning("No custom aggregators to remove.")
                return
            label = _ask(
                _select(
                    "Which aggregator do you want to remove?",
                    [_custom_label(c) for c in custom],
                )
            )
            if label is None:
                return
            remaining = [c for c in custom if _custom_label(c) != label]
            if len(remaining) == len(custom):
                return
            if remaining:
                platforms["custom"] = remaining
            else:
                platforms.pop("custom", None)
            changed = True
            log.info("Removed %s.", label)

    while True:
        custom = platforms.get("custom") or []
        log.info(
            "  Aggregator feeds: %s | Custom aggregators: %s",
            "on" if platforms.get("aggregators") else "off",
            ", ".join(_custom_label(c) for c in custom) if custom else "(none)",
        )
        action = _menu(
            "Which aggregator change do you want to make?", _AGGREGATOR_CHOICES
        )
        if action is None:
            return changed
        try:
            apply_choice(action)
        except _GoBack:
            continue


def _run_toolbox(
    profile_data: Optional[Dict],
    working_path: Optional[str],
    dirty: bool,
) -> Tuple[Optional[Dict], Optional[str], bool, bool]:
    """Run the toolbox as its own menu level.

    Returns ``(profile_data, working_path, dirty, exit_requested)``. Back and Esc
    return to the launchpad; only the explicit Exit entry asks for the whole wizard
    to close.
    """
    while True:
        action = _menu("Open the toolbox:", _toolbox_choices())
        if action is None:
            return profile_data, working_path, dirty, False

        if action == MENU_EXIT:
            return profile_data, working_path, dirty, True
        if action == MENU_EDIT:
            loaded = _load_profile_flow()
            if loaded:
                working_path, profile_data = loaded
                dirty = False
            continue
        if action == MENU_SOURCES:
            if _require_profile(profile_data):
                dirty = _edit_with_back(_edit_sources, profile_data) or dirty
            continue
        if action == MENU_ENGINES:
            _run_action(_manage_engines)
            continue
        if action == MENU_AGGREGATORS:
            if _require_profile(profile_data):
                dirty = _edit_with_back(_edit_aggregators, profile_data) or dirty
            continue
        if action == MENU_DEBUG:
            if _require_profile(profile_data):
                profile_data["debug"] = not bool(profile_data.get("debug"))
                dirty = True
                log.info("Debug logging: %s", "on" if profile_data["debug"] else "off")
            continue
        if action == MENU_HELP:
            _run_action(_show_help_menu)
            continue
        if action == MENU_LOGS:
            _run_action(_show_recent_logs)
            continue
        if action == MENU_CONVERT:
            _run_action(_ask_convert_document)
            continue
        if action == MENU_UPDATE:
            _run_action(lambda: print(update_sweepy()))
            continue


def run_wizard(
    profile_path: Optional[str] = None,
    run_sweep: Optional[Callable[[Dict, Optional[str]], None]] = None,
) -> Optional[str]:
    """Open the menu, calling ``run_sweep(profile_data, profile_path)`` when a sweep is requested."""
    _print_welcome_banner()

    working_path: Optional[str] = None
    profile_data: Optional[Dict] = None
    dirty = False

    try:
        if profile_path:
            loaded = _load_profile_flow(profile_path)
            if loaded:
                working_path, profile_data = loaded

        while True:
            try:
                action = _ask(_wizard_menu_select(profile_data))
            except _GoBack:
                action = MENU_EXIT
            if action is None:
                action = MENU_EXIT

            if action == MENU_TOOLBOX:
                profile_data, working_path, dirty, exit_requested = _run_toolbox(
                    profile_data, working_path, dirty
                )
                if not exit_requested:
                    continue
                action = MENU_EXIT

            if action == MENU_EXIT:
                if dirty and profile_data is not None:
                    try:
                        save = _ask(
                            questionary.confirm("Save your changes before exiting?", default=True)
                        )
                    except _GoBack:
                        save = False
                    if save:
                        working_path = _save_profile_flow(profile_data, working_path) or working_path
                return working_path
            if action == MENU_RUN:
                _run_loaded_profile(profile_data, working_path, run_sweep)
                continue
            if action == MENU_CREATE:
                created = _create_profile_flow()
                if created:
                    working_path, profile_data = created
                    dirty = False
                continue
            if action == MENU_LOAD:
                loaded = _load_saved_profile_flow()
                if loaded:
                    working_path, profile_data = loaded
                    dirty = False
                continue
            if action == MENU_EDIT:
                loaded = _load_profile_flow()
                if loaded:
                    working_path, profile_data = loaded
                    dirty = False
                continue
            if action == MENU_DEBUG:
                if _require_profile(profile_data):
                    profile_data["debug"] = not bool(profile_data.get("debug"))
                    dirty = True
                    log.info(
                        "Debug logging: %s", "on" if profile_data["debug"] else "off"
                    )
                continue
            if action == MENU_SCALING:
                if _require_profile(profile_data):
                    dirty = _edit_with_back(_edit_scaling, profile_data) or dirty
                continue
            if action == MENU_AGGREGATORS:
                if _require_profile(profile_data):
                    dirty = _edit_with_back(_edit_aggregators, profile_data) or dirty
                continue
            if action == MENU_SOURCES:
                if _require_profile(profile_data):
                    dirty = _edit_with_back(_edit_sources, profile_data) or dirty
                continue
            if action == MENU_ENGINES:
                _run_action(_manage_engines)
                continue
            if action == MENU_HELP:
                _run_action(_show_help_menu)
                continue
            if action == MENU_LOGS:
                _run_action(_show_recent_logs)
                continue
            if action == MENU_CONVERT:
                _run_action(_ask_convert_document)
                continue
            if action == MENU_UPDATE:
                _run_action(lambda: print(update_sweepy()))
                continue
    except (KeyboardInterrupt, EOFError):
        print("Setup cancelled — no profile saved.")
        sys.exit(0)


def save_profile(profile_data: dict, file_path: Optional[str] = None) -> str:
    """Saves a profile configuration dict to YAML."""
    if not file_path:
        name = profile_data.get("name", "user")
        titles = profile_data.get("search", {}).get("titles", ["custom"])
        first_title = titles[0] if titles else "custom"
        safe_name = re.sub(r'[^a-zA-Z0-9]+', '_', name).strip('_').lower()
        safe_title = re.sub(r'[^a-zA-Z0-9]+', '_', first_title).strip('_').lower()
        file_path = f"profiles/{safe_name}_{safe_title}.yaml"

    os.makedirs(os.path.dirname(file_path) or "profiles", exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(profile_data, f, sort_keys=False, default_flow_style=False)

    log.info("Profile saved to: %s", file_path)
    record_last_profile(file_path)
    return file_path


def load_config(config_path):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        profile = yaml.safe_load(f)
    if not isinstance(profile, dict):
        raise ValueError(f"Configuration file must contain a YAML mapping: {config_path}")
    return profile
