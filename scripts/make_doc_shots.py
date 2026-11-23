"""Render Sweepy's documentation screenshots from the shipped renderers.

Every image in this set comes from the product rather than from a mock:

* the launchpad panels build ``engine.config._wizard_menu_select`` and read its
  ``FormattedTextControl`` fragments, so tile names and layout track the code;
* the prompt and menu panels capture the message and choices that
  ``engine.config`` passes to questionary, then lay them out the way
  questionary 2.1.1 draws them;
* the stage panel reads the ``log_fn`` stage lines out of ``swee.py``;
* the card panels take their text and colors from a rendered report PDF.

Colors resolve through the same style tables the product uses, so a palette
change shows up on the next run.

Run from the repo root:

    python scripts/make_doc_shots.py --out ../docusaurus/docs/sweepy/screenshots
    python scripts/make_doc_shots.py --out docs/screenshots \\
        --report results/<assessed>.pdf --wizard docs/<wizard-run>.pdf

Set ``PYTHONIOENCODING=utf-8`` when stdout is redirected. Otherwise
``config.BACK_LABEL`` falls back to ``< Back`` and the menu panel stops
matching the terminal it documents.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymupdf  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from prompt_toolkit.input import DummyInput  # noqa: E402
from prompt_toolkit.output import DummyOutput  # noqa: E402

from engine import config  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

BACKGROUND = "#111113"
DEFAULT_TEXT = "#e0dfdf"
TITLEBAR = "#1b1b1f"
TITLE_TEXT = "#9da5b0"
DOTS = ("#ff5f56", "#ffbd2e", "#27c93f")
CURSOR = "\u258c"

FONT_REGULAR = r"C:\Windows\Fonts\consola.ttf"
FONT_BOLD = r"C:\Windows\Fonts\consolab.ttf"
FONT_ITALIC = r"C:\Windows\Fonts\consolai.ttf"

FONT_SIZE = 18
PAD_X = 40
PAD_Y = 22
TITLEBAR_HEIGHT = 40
TITLE_FONT_SIZE = 13
DOT_RADIUS = 6
DOT_LEFT = 24
DOT_GAP = 22

ALEX = {
    "name": "Alex Rivera",
    "search": {
        "titles": [
            "Paralegal",
            "Legal Assistant",
            "Litigation Support Specialist",
            "Legal Secretary",
        ]
    },
    "resume": {"path": "docs/Alex_Rivera_Resume.pdf"},
}

Rgb = Tuple[int, int, int]
Style = Tuple[Rgb, Optional[Rgb], bool, bool]  # color, background, bold, italic
Run = Tuple[str, Rgb, bool, bool, Optional[Rgb]]  # text, color, bold, italic, background


def rgb(value: str | None, fallback: str = DEFAULT_TEXT) -> Rgb:
    text = (value or fallback).lstrip("#")
    if len(text) != 6:
        text = fallback.lstrip("#")
    return tuple(int(text[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def style_table(style) -> dict:
    """Turn a prompt_toolkit style into ``{class name: (color, background, bold, italic)}``."""
    table = {}
    for name, spec in style.style_rules:
        if not name or ":" in name:
            continue
        color = None
        background = None
        for part in spec.split():
            if part.startswith("fg:"):
                color = part[3:]
            elif part.startswith("bg:"):
                background = part[3:]
        table[name] = (
            rgb(color) if color else rgb(DEFAULT_TEXT),
            rgb(background) if background else None,
            "bold" in spec,
            "italic" in spec,
        )
    return table


def prompt_style() -> dict:
    return style_table(config._MENU_STYLE)


def run(text: str, style: Style) -> Run:
    """Pair text with a style table entry, keeping the background behind it."""
    color, background, is_bold, is_italic = style
    return (text, color, is_bold, is_italic, background)


def as_rows(runs: Iterable[Run]) -> List[List[Run]]:
    """Split runs on newlines so the canvas can place them row by row."""
    rows: List[List[Run]] = [[]]
    for text, color, bold, italic, background in runs:
        for index, chunk in enumerate(text.split("\n")):
            if index:
                rows.append([])
            if chunk:
                rows[-1].append((chunk, color, bold, italic, background))
    return [row for row in rows if row]


def draw_shot(rows: Sequence[Sequence[Run]], title: str, target: Path) -> None:
    regular = ImageFont.truetype(FONT_REGULAR, FONT_SIZE)
    bold = ImageFont.truetype(FONT_BOLD, FONT_SIZE)
    italic = ImageFont.truetype(FONT_ITALIC, FONT_SIZE)
    title_font = ImageFont.truetype(FONT_REGULAR, TITLE_FONT_SIZE)

    # Terminals place every glyph on the font's own line box, so the cell pitch is
    # the ascent plus descent. Any larger pitch leaves gaps between vertical rules.
    ascent, descent = regular.getmetrics()
    line_height = ascent + descent
    cell = float(round(regular.getlength("M")))
    columns = max(sum(len(text) for text, *_ in row) for row in rows)
    width = int(cell * columns) + PAD_X * 2
    height = TITLEBAR_HEIGHT + PAD_Y * 2 + line_height * len(rows)

    image = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, width, TITLEBAR_HEIGHT], fill=TITLEBAR)
    for index, color in enumerate(DOTS):
        center_x = DOT_LEFT + index * DOT_GAP
        draw.ellipse(
            [
                center_x - DOT_RADIUS,
                TITLEBAR_HEIGHT // 2 - DOT_RADIUS,
                center_x + DOT_RADIUS,
                TITLEBAR_HEIGHT // 2 + DOT_RADIUS,
            ],
            fill=color,
        )
    draw.text((DOT_LEFT + 3 * DOT_GAP + 10, 12), title, font=title_font, fill=TITLE_TEXT)

    y = TITLEBAR_HEIGHT + PAD_Y
    for row in rows:
        column = 0
        for text, color, is_bold, is_italic, background in row:
            if background is not None and text:
                draw.rectangle(
                    [
                        PAD_X + column * cell,
                        y,
                        PAD_X + (column + len(text)) * cell,
                        y + line_height,
                    ],
                    fill=background,
                )
            for character in text:
                if is_bold and ord(character) < 128:
                    font = bold
                elif is_italic and ord(character) < 128:
                    font = italic
                else:
                    font = regular
                draw.text((PAD_X + column * cell, y), character, font=font, fill=color)
                column += 1
        y += line_height

    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)
    print(f"{target.name}  {image.width}x{image.height}")


def launchpad_runs(profile, columns: str) -> List[Run]:
    os.environ["COLUMNS"] = columns
    wrapper = config._wizard_menu_select(profile, input=DummyInput(), output=DummyOutput())
    application = wrapper.application
    fragments = application.layout.container.content.text()
    table = style_table(application.style)
    runs: List[Run] = []
    for style_str, text in fragments:
        name = style_str.removeprefix("class:")
        style = table.get(name, (rgb(DEFAULT_TEXT), None, False, False))
        runs.append(run(text, style))
    return runs


def captured_text_prompt(ask, *args) -> str:
    """Run a wizard step with questionary stubbed out and return its message."""
    original_text = config.questionary.text
    original_ask = config._ask
    captured = {}

    def fake_text(message, **_kwargs):
        captured["message"] = message
        return object()

    config.questionary.text = fake_text
    config._ask = lambda _question: None
    try:
        ask(*args)
    finally:
        config.questionary.text = original_text
        config._ask = original_ask
    return captured["message"]


def captured_menu(choices_source) -> Tuple[str, List[str]]:
    """Run the review screen with the select prompt stubbed and return its menu."""
    original_select = config._select
    captured = {}

    def fake_select(message, choices, **_kwargs):
        captured["message"] = message
        captured["choices"] = [str(choice) for choice in choices]
        raise config._GoBack()

    config._select = fake_select
    try:
        choices_source()
    except config._GoBack:
        pass
    finally:
        config._select = original_select
    return captured["message"], captured["choices"]


def text_prompt_runs(message: str) -> List[List[Run]]:
    table = prompt_style()
    qmark = table["qmark"]
    question = table["question"]
    body = table["text"]
    return as_rows(
        [
            run("?", qmark),
            run(f" {message} ", question),
            run(CURSOR, body),
        ]
    )


def select_runs(message: str, choices: Sequence[str], pointed_at: int) -> List[List[Run]]:
    """Lay out a questionary select the way questionary 2.1.1 draws it.

    Each row carries the ``»`` pointer, the ``○`` indicator, and the button title.
    """
    table = prompt_style()
    qmark = table["qmark"]
    question = table["question"]
    pointer = table["pointer"]
    highlighted = table["highlighted"]
    plain = table["text"]

    rows: List[List[Run]] = [[run("?", qmark), run(f" {message} ", question)]]
    for index, title in enumerate(choices):
        if index == pointed_at:
            rows.append([run(" \u00bb ", pointer), run("\u25cb ", plain), run(title, highlighted)])
        else:
            rows.append([run("   ", plain), run("\u25cb ", plain), run(title, plain)])
    return rows


def stage_lines() -> List[List[Run]]:
    """Read the numbered stage lines straight out of ``swee.py``."""
    source = (ROOT / "swee.py").read_text(encoding="utf-8")
    rows: List[List[Run]] = []
    for blank, number, label in re.findall(r'log_fn\("(\\n)?\[(\d)/5\] ([^"]*)"\)', source):
        if blank:
            rows.append([])
        rows.append([(f"[{number}/5] {label}", rgb(DEFAULT_TEXT), False, False, None)])
    return rows


def _styled_runs(line) -> List[Run]:
    runs: List[Run] = []
    for span in line["spans"]:
        value = int(span["color"])
        color = ((value >> 16) & 255, (value >> 8) & 255, value & 255)
        is_bold = "Bold" in span["font"] or span["flags"] & 16 == 16
        runs.append((span["text"], color, is_bold, False, None))
    return runs


def pdf_lines(pdf_path: Path) -> List[Tuple[float, str, List[Run]]]:
    document = pymupdf.open(pdf_path)
    try:
        found = []
        for block in document[0].get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                runs = _styled_runs(line)
                found.append((line["bbox"][1], "".join(run[0] for run in runs), runs))
        found.sort(key=lambda item: item[0])
        return found
    finally:
        document.close()


def pdf_first_line(pdf_path: Path, needle: str) -> List[Run]:
    """Return the first report line that contains ``needle``."""
    for _y, text, runs in pdf_lines(pdf_path):
        if needle in text:
            return runs
    raise SystemExit(f"{needle!r} not found in {pdf_path}")


def pdf_spans(pdf_path: Path, needle: str) -> List[Run]:
    """Return only the spans that contain ``needle``, colors included."""
    for _y, text, runs in pdf_lines(pdf_path):
        if needle in text:
            return [run for run in runs if needle in run[0]]
    raise SystemExit(f"{needle!r} not found in {pdf_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="docs/screenshots", help="Directory for the PNGs.")
    parser.add_argument(
        "--report",
        default="",
        help="Assessed report PDF. Supplies the MATCH card panels.",
    )
    parser.add_argument(
        "--wizard",
        default="",
        help=(
            "Report PDF that still prints KEYWORD OVERLAP, such as the committed "
            "docs/sample_report.pdf from before an assessment replaced its labels. "
            "Supplies the 08 and 09 panels together with --report."
        ),
    )
    args = parser.parse_args()
    out = Path(args.out)

    draw_shot(as_rows(launchpad_runs(None, "94")), "Terminal  \u2014  sweepy --setup", out / "sweepy-01-launchpad-empty.png")
    draw_shot(as_rows(launchpad_runs(ALEX, "94")), "Terminal  \u2014  sweepy --setup", out / "sweepy-02-launchpad-loaded.png")
    draw_shot(as_rows(launchpad_runs(ALEX, "72")), "Tile = verb + object; subtitle = user goal", out / "sweepy-03-tile-subtitles.png")

    titles = captured_text_prompt(config._ask_titles, None)
    draw_shot(text_prompt_runs(titles), "Wizard  \u2014  job titles", out / "sweepy-04-wizard-titles.png")

    salary = captured_text_prompt(config._ask_min_salary, None)
    draw_shot(text_prompt_runs(salary), "Wizard  \u2014  minimum salary", out / "sweepy-05-wizard-salary.png")

    message, choices = captured_menu(lambda: config._review_answers({}, [], lambda: {}))
    buttons = [choice.title for choice in config._button_choices(choices)]
    draw_shot(
        select_runs(message, buttons, pointed_at=2),
        "sweepy --setup  \u2014  post-wizard menu",
        out / "sweepy-06-post-wizard-menu.png",
    )

    draw_shot(stage_lines(), "Terminal  \u2014  sweepy --run", out / "sweepy-07-progress-mid.png")

    if args.report and args.wizard:
        matched = pdf_first_line(Path(args.report), "SUBMIT")
        overlap = pdf_first_line(Path(args.wizard), "SUBMIT")
        draw_shot(
            as_rows(matched) + [[]] + as_rows(overlap),
            "Same number, two different labels",
            out / "sweepy-08-score-label.png",
        )
        standard = pdf_spans(Path(args.report), "STANDARD / QUICK APPLY")
        extended = pdf_spans(Path(args.report), "EXTENDED RESPONSES REQUIRED")
        draw_shot(
            as_rows(standard) + as_rows(extended),
            "Report card badges",
            out / "sweepy-09-status-badges.png",
        )


if __name__ == "__main__":
    main()
