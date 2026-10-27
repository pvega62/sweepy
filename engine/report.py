from __future__ import annotations

import logging
import os
import re
from io import BytesIO
from typing import List
from urllib.parse import urlsplit
from xml.sax.saxutils import escape as _xml_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from engine.enrich import get_tracks
from engine.portfolio import get_portfolio

log = logging.getLogger("sweepy.engine.report")

# Design tokens (faithful to the reference generator).
PRIMARY = colors.HexColor("#0F172A")            # Slate 900
BRAND_BLUE = colors.HexColor("#1D4ED8")         # Blue 700
TEXT_DARK = colors.HexColor("#1E293B")          # Slate 800
TEXT_MUTED = colors.HexColor("#475569")         # Slate 600
BORDER = colors.HexColor("#CBD5E1")             # Slate 300
BG_LIGHT = colors.HexColor("#F8FAFC")           # Slate 50
TAG = colors.HexColor("#0F766E")                # Teal 700
BG_HIGHLIGHT = colors.HexColor("#FFFBEB")       # Amber 50
BORDER_HIGHLIGHT = colors.HexColor("#F59E0B")   # Amber 500

_CARD_WIDTH = 544


def _esc(value) -> str:
    return _xml_escape(str(value if value is not None else ""))


def _make_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "DocTitle", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=12.2, leading=15.2, textColor=PRIMARY,
    ))
    styles.add(ParagraphStyle(
        "MetaStyle", parent=styles["Normal"], fontName="Helvetica",
        fontSize=7.4, leading=10.0, textColor=TEXT_MUTED,
    ))
    styles.add(ParagraphStyle(
        "JobTitle", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=8.8, leading=11.2, textColor=PRIMARY,
    ))
    styles.add(ParagraphStyle(
        "CompanyBadge", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=7.1, leading=8.8, textColor=TAG,
    ))
    styles.add(ParagraphStyle(
        "JobBody", parent=styles["Normal"], fontName="Helvetica",
        fontSize=7.2, leading=9.6, textColor=TEXT_DARK,
    ))
    styles.add(ParagraphStyle(
        "ReqStyle", parent=styles["Normal"], fontName="Helvetica",
        fontSize=6.8, leading=8.6, textColor=TEXT_MUTED,
    ))
    styles.add(ParagraphStyle(
        "JobLink", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=7.1, leading=9.0, textColor=BRAND_BLUE,
    ))
    return styles


def _match_label(job: dict) -> str:
    value = int(job.get("match_value", 0))
    kind = job.get("match_kind", "overlap")
    label = "MATCH" if kind == "match" else "KEYWORD OVERLAP"
    return f"{value}% {label}"


def _fit_label(job: dict) -> str:
    """Name the portfolio-fit score, or an empty string when none was submitted."""
    raw = job.get("portfolio_fit")
    if raw is None or str(raw).strip() == "":
        return ""
    try:
        return f"{int(raw)}% PORTFOLIO FIT"
    except (TypeError, ValueError):
        return ""


def _track_names(profile: dict) -> List[str]:
    return [str(t.get("name", "") or "") for t in get_tracks(profile)]


def _platforms_label(cards: List[dict]) -> str:
    plats = sorted({str(c.get("platform", "") or "") for c in cards if c.get("platform")})
    return " & ".join(plats) if plats else "Direct ATS Boards"


def _title_text(profile: dict) -> str:
    titles = profile.get("search", {}).get("titles", []) or []
    label = " & ".join(str(t) for t in titles) if titles else "Job"
    return f"{label} Openings"


def _meta_html(profile: dict, cards: List[dict]) -> str:
    name = _esc(profile.get("name", "Job Seeker"))
    location = _esc((profile.get("search", {}) or {}).get("location", ""))
    tracks = _track_names(profile)
    tracks_label = (
        " vs ".join(_esc(t) for t in tracks) if len(tracks) > 1 else (_esc(tracks[0]) if tracks else "Resume")
    )
    platforms = _esc(_platforms_label(cards))
    n = len(cards)
    portfolio_line = ""
    routing = _portfolio_routing(profile)
    if routing:
        portfolio_line = f"<br/><b>Portfolio Routing:</b> {routing}"
    return (
        f"<b>Audited For:</b> {name} ({location}) | <b>Dual Resume Targeting:</b> {tracks_label}<br/>"
        f"<b>Platforms Covered:</b> {platforms} | <b>Sorted:</b> Highest to Lowest Match % ({n} Live Links)"
        f"{portfolio_line}<br/>"
        '<b>Highlight Legend:</b> <font color="#B45309"><b>Amber Highlighted Cards = Extended Written '
        'Responses Required</b></font> | Slate Cards = Standard / Quick Apply | '
        '<font color="#0F766E"><b>PORTFOLIO FIT</b></font> = how well that track\'s '
        'samples cover the posting, scored apart from the match percentage.'
    )


def _portfolio_target(source: dict) -> str:
    """Name the portfolio a track submits: its link, or the file name when it is local."""
    return source.get("url") or os.path.basename(source.get("path") or "")


def _portfolio_routing(profile: dict) -> str:
    """Map each configured track to the portfolio that track submits."""
    sources = get_portfolio(profile)["sources"]
    if not sources:
        return ""
    parts = [
        f"{_esc(source.get('track') or 'All tracks')} &#8594; {_esc(_portfolio_target(source))}"
        for source in sources
    ]
    return " | ".join(parts)


def _portfolio_line(job: dict) -> str:
    """Build the card's portfolio row, or an empty string when the card has none."""
    url = _xml_escape(str(job.get("portfolio_url", "") or ""))
    path = str(job.get("portfolio_path", "") or "")
    pieces = [str(piece) for piece in (job.get("portfolio_pieces") or []) if str(piece).strip()]
    highlight = str(job.get("portfolio_highlight", "") or "").strip()
    if not (url or path or pieces or highlight):
        return ""

    if url:
        target = f'<a href="{url}"><b>[{_esc(_link_label(job.get("portfolio_url")))}]</b></a>'
    elif path:
        target = f"<b>{_esc(os.path.basename(path))}</b>"
    else:
        target = ""
    body = f"<b>Portfolio:</b> {target}".strip()
    label, value = ("Highlight", highlight) if highlight else ("Pieces", ", ".join(pieces))
    if value:
        body += f' &nbsp;|&nbsp; <b>{label}:</b> <font color="#1D4ED8">{_esc(value)}</font>'
    return body


def _link_label(url) -> str:
    """Shorten a portfolio link to its host and first path segment.

    Several tracks can live on one host (/uxwriting and /technical-writing-hardware
    both sit on pvega62.github.io), so the host alone would not say which
    portfolio the card sends.
    """
    parts = urlsplit(str(url or ""))
    host = parts.netloc
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return "open"
    segment = next((p for p in parts.path.split("/") if p), "")
    return f"{host}/{segment}" if segment else host


def _page_theme(page_jobs: List[dict], page_num: int) -> str:
    ranks = [int(c.get("rank", 0)) for c in page_jobs]
    lo, hi = min(ranks), max(ranks)
    return f"Page {page_num}: Ranks {lo}-{hi}"


def _page_subtitle_html(page_jobs: List[dict], page_num: int) -> str:
    ranks = [int(c.get("rank", 0)) for c in page_jobs]
    scores = [int(c.get("match_value", 0)) for c in page_jobs]
    lo, hi = min(ranks), max(ranks)
    hi_score, lo_score = max(scores), min(scores)
    subtitle = f"<b>Page {page_num}: Ranks {lo}-{hi} ({hi_score}% - {lo_score}%)</b>"
    domains = [str(c.get("domain", "") or "") for c in page_jobs if c.get("domain")]
    if domains:
        subtitle += f" // {', '.join(domains)}"
    return subtitle


def _render_card(job: dict, styles: dict) -> Table:
    rank = int(job.get("rank", 0))
    company = _esc(job.get("company", ""))
    domain = _esc(job.get("domain", "")).upper()
    match_label = _match_label(job)
    fit_label = _fit_label(job)
    resume_color = job.get("resume_color", "#1D4ED8") or "#1D4ED8"
    resume_track = _esc(job.get("resume_track", ""))
    has_extended = bool(job.get("has_extended_response", False))

    resp_badge = (
        '<font color="#B45309"><b>[EXTENDED RESPONSES REQUIRED]</b></font>'
        if has_extended
        else '<font color="#64748B"><b>[STANDARD / QUICK APPLY]</b></font>'
    )
    # Portfolio fit sits beside the match score so the two reads stay comparable;
    # a card without a submitted fit omits the segment entirely.
    fit_html = (
        f'<font color="#0F766E"><b>[{fit_label}]</b></font> &nbsp;|&nbsp; '
        if fit_label
        else ""
    )
    badge_line = (
        f"<b>#{rank} // {company.upper()}</b> &nbsp;|&nbsp; "
        f'<font color="#1E40AF"><b>[{match_label}]</b></font> &nbsp;|&nbsp; '
        f"{fit_html}"
        f'<font color="{resume_color}"><b>[SUBMIT: {resume_track}]</b></font> &nbsp;|&nbsp; '
        f"{resp_badge} &nbsp;|&nbsp; {domain}"
    )

    title = _esc(job.get("title", ""))
    location = _esc(job.get("location", ""))
    summary = _esc(job.get("summary", ""))
    requirements = _esc(job.get("requirements", ""))
    alignment = _esc(job.get("alignment", ""))
    concerns = _esc(job.get("concerns", ""))
    # The concern shares the tip's line: a separate row pushed short cards past the
    # six-per-page target. Reportlab wraps the pair when both run long.
    concern_html = (
        f' &nbsp;|&nbsp; <b>Working Against You:</b> <font color="#B91C1C">{concerns}</font>'
        if concerns
        else ""
    )
    comp = _esc(job.get("comp", ""))
    benefits = _esc(job.get("benefits", ""))
    app_format = _esc(job.get("app_format", ""))
    portfolio_html = _portfolio_line(job)
    url = _xml_escape(job.get("url", "") or "#")
    platform = _esc(job.get("platform", ""))

    if has_extended:
        # The deterministic app_format already starts with "Extended Written Prompts";
        # the renderer's own "Extended Written Response:" label makes that prefix redundant.
        body = app_format
        for prefix in ("Extended Written Prompts", "Extended Written Response"):
            if body.startswith(prefix):
                body = body[len(prefix):].lstrip(": ").strip()
                break
        format_p = (
            f'<b>Application Format:</b> <font color="#B45309"><b>Extended Written Response:</b> '
            f'{body}</font>'
        )
        card_bg = BG_HIGHLIGHT
        card_border = BORDER_HIGHLIGHT
        card_border_width = 1.0
    else:
        format_p = f'<b>Application Format:</b> <font color="#475569">{app_format}</font>'
        card_bg = BG_LIGHT
        card_border = BORDER
        card_border_width = 0.75

    card_data = [
        Paragraph(badge_line, styles["CompanyBadge"]),
        Spacer(1, 0.4),
        Paragraph(f"<b>{title}</b> | <font color=\"#475569\">{location}</font>", styles["JobTitle"]),
        Spacer(1, 0.6),
        Paragraph(f"<b>Overview:</b> {summary}", styles["JobBody"]),
        Spacer(1, 0.3),
        Paragraph(f"<b>Key Requirements:</b> {requirements}", styles["ReqStyle"]),
        Spacer(1, 0.3),
        Paragraph(
            f"<b>Application Tip:</b> <font color=\"#0F766E\">{alignment}</font>"
            f"{concern_html}",
            styles["ReqStyle"],
        ),
        Spacer(1, 0.3),
        Paragraph(
            f"<b>Comp &amp; Benefits:</b> <font color=\"#047857\"><b>{comp}</b></font> "
            f"&nbsp;|&nbsp; {benefits}",
            styles["ReqStyle"],
        ),
        Spacer(1, 0.3),
        Paragraph(format_p, styles["ReqStyle"]),
        *(
            [Paragraph(portfolio_html, styles["ReqStyle"])]
            if portfolio_html
            else []
        ),
        Spacer(1, 0.8),
        Paragraph(f'<a href="{url}"><b>[Apply on {platform} Job Board]</b></a>', styles["JobLink"]),
    ]

    card_table = Table([[card_data]], colWidths=[_CARD_WIDTH])
    card_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), card_bg),
        ("BOX", (0, 0), (-1, -1), card_border_width, card_border),
        ("TOPPADDING", (0, 0), (-1, -1), 1.8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
        ("LEFTPADDING", (0, 0), (-1, -1), 6.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6.5),
    ]))
    return card_table


def _default_playbook(cards: List[dict], profile: dict) -> str:
    amber = [c for c in cards if c.get("has_extended_response")]
    slate = [c for c in cards if not c.get("has_extended_response")]
    tracks = get_tracks(profile)

    parts = ["<b>APPLICATION STRATEGY // DUAL RESUME ROUTING &amp; WORKFLOW PLAYBOOK</b><br/>"]

    if amber:
        names = ", ".join(
            f"<b>{_esc(c.get('company',''))} (#{c.get('rank', 0)}, {c.get('match_value', 0)}%)</b>"
            for c in amber
        )
        parts.append(
            f"<b>- EXTENDED RESPONSE APPLICATIONS (Draft Prompts First // "
            f"{len(amber)} Roles Highlighted in Amber):</b><br/>"
        )
        parts.append(f"&nbsp;&nbsp;- {names}.<br/>")

    if slate:
        names = ", ".join(
            f"<b>{_esc(c.get('company',''))} (#{c.get('rank', 0)})</b>" for c in slate
        )
        parts.append(
            f"<b>- STANDARD / QUICK SUBMISSION APPLICATIONS ({len(slate)} Roles in Slate):</b><br/>"
        )
        parts.append(f"&nbsp;&nbsp;- {names}.<br/>")

    if tracks:
        counts = {}
        for c in cards:
            key = str(c.get("resume_track", "") or "")
            counts[key] = counts.get(key, 0) + 1
        routing = "; ".join(
            f"<code>{_esc(t.get('name',''))}</code> for {counts.get(str(t.get('name','')), 0)} roles"
            for t in tracks
        )
        parts.append(f"<b>- RESUME TARGETING:</b> Submit {routing}.")

    sources = get_portfolio(profile)["sources"]
    if sources:
        highlighted = sum(
            1 for c in cards if str(c.get("portfolio_highlight") or "").strip()
        )
        links = "; ".join(
            f"<code>{_esc(source.get('track') or 'All tracks')}</code> submits "
            f"{_esc(_portfolio_target(source))}"
            for source in sources
        )
        parts.append(
            f"<br/><b>- PORTFOLIO SOURCES:</b> {links}. "
            f"{highlighted} role(s) name the pieces to highlight.<br/>"
        )

    return "".join(parts)


_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.S)


def playbook_to_markup(text: str) -> str:
    """Convert playbook prose into ReportLab paragraph markup.

    The playbook arrives as prose, so ``&`` and angle brackets get escaped instead of
    reaching ReportLab's parser, and newlines become line breaks. ``**bold**`` still
    adds emphasis.
    """
    lines = (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    markup = [_BOLD_RE.sub(r"<b>\1</b>", _xml_escape(line)).strip() for line in lines]
    while markup and not markup[0]:
        markup.pop(0)
    while markup and not markup[-1]:
        markup.pop()
    return "<br/>".join(markup)


def _playbook_table(playbook_html: str, styles: dict) -> Table:
    playbook_p = Paragraph(
        playbook_html,
        ParagraphStyle(
            "Playbook", parent=styles["Normal"], fontName="Helvetica",
            fontSize=6.6, leading=8.2, textColor=TEXT_DARK,
        ),
    )
    table = Table([[playbook_p]], colWidths=[_CARD_WIDTH])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#BFDBFE")),
        ("TOPPADDING", (0, 0), (-1, -1), 1.8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
        ("LEFTPADDING", (0, 0), (-1, -1), 6.0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6.0),
    ]))
    return table


def _flowable_height(flowable, width: float, measurement_canvas: Canvas) -> float:
    _, height = flowable.wrapOn(measurement_canvas, width, 100000)
    return height + flowable.getSpaceBefore() + flowable.getSpaceAfter()


def _page_header(
    page_num: int,
    page_jobs: List[dict],
    title_text: str,
    meta_html: str,
    styles: dict,
) -> List:
    if page_num == 1:
        header = [
            Paragraph(title_text, styles["DocTitle"]),
            Spacer(1, 0.8),
            Paragraph(meta_html, styles["MetaStyle"]),
        ]
    else:
        override = next((c.get("page_theme") for c in page_jobs if c.get("page_theme")), "")
        subtitle = f"<b>{_esc(override)}</b>" if override else _page_subtitle_html(page_jobs, page_num)
        header = [
            Paragraph(f"{title_text} (Cont.)", styles["DocTitle"]),
            Spacer(1, 0.8),
            Paragraph(subtitle, styles["MetaStyle"]),
        ]
    header.extend([
        Spacer(1, 1.8),
        HRFlowable(width="100%", thickness=1, color=BORDER, spaceBefore=0, spaceAfter=2.5),
    ])
    return header


def _paginate(
    cards: List[dict],
    per_page: int,
    title_text: str,
    meta_html: str,
    styles: dict,
    playbook: Table,
    page_width: float,
    page_height: float,
) -> List[List[dict]]:
    per_page = max(1, per_page)
    measurement_canvas = Canvas(BytesIO(), pagesize=letter)
    card_blocks = [(_render_card(card, styles), Spacer(1, 2.2)) for card in cards]
    playbook_height = _flowable_height(Spacer(1, 0.8), page_width, measurement_canvas)
    playbook_height += _flowable_height(playbook, page_width, measurement_canvas)
    pages = []
    next_card = 0

    while next_card < len(cards):
        page_num = len(pages) + 1
        page_jobs = []
        used_height = 0.0

        while next_card + len(page_jobs) < len(cards) and len(page_jobs) < per_page:
            index = next_card + len(page_jobs)
            candidate_jobs = page_jobs + [cards[index]]
            header = _page_header(page_num, candidate_jobs, title_text, meta_html, styles)
            header_height = sum(
                _flowable_height(item, page_width, measurement_canvas)
                for item in header
            )
            card, gap = card_blocks[index]
            card_height = (
                _flowable_height(card, page_width, measurement_canvas)
                + _flowable_height(gap, page_width, measurement_canvas)
            )
            # The playbook prints once, after the final card, so only the card that
            # completes the set reserves room for it. Reserving on every page cost
            # card slots on each page for a box that renders on the last one.
            reserve = playbook_height if index == len(cards) - 1 else 0.0
            if page_jobs and header_height + used_height + card_height + reserve > page_height:
                break
            page_jobs.append(candidate_jobs[-1])
            used_height += card_height

        pages.append(page_jobs)
        next_card += len(page_jobs)

    return pages


def build_report(jobs: List[dict], output_path: str, profile: dict, playbook: str = "") -> int:
    """Render the cards PDF and return the total page count."""
    report = profile.get("report", {}) or {}
    cards_per_page = int(report.get("cards_per_page", 6) or 6)
    # A blank or missing max_cards falls back to 24; 0 or less means no cap.
    raw_max_cards = report.get("max_cards")
    max_cards = 24 if raw_max_cards in (None, "") else int(raw_max_cards)

    cards = list(jobs) if max_cards <= 0 else list(jobs)[:max_cards]
    styles = _make_styles()
    title_text = _title_text(profile)
    meta_html = _meta_html(profile, cards)
    playbook_markup = playbook_to_markup(playbook) if playbook.strip() else ""
    playbook_table = _playbook_table(playbook_markup or _default_playbook(cards, profile), styles)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    temp_path = output_path + ".tmp.pdf"
    doc = SimpleDocTemplate(
        temp_path, pagesize=letter,
        leftMargin=34, rightMargin=34, topMargin=22, bottomMargin=22,
    )
    pages = _paginate(
        cards,
        cards_per_page,
        title_text,
        meta_html,
        styles,
        playbook_table,
        doc.width,
        doc.height,
    ) if cards else []
    total_pages = max(1, len(pages))

    story = []

    if not cards:
        story.append(Paragraph(title_text, styles["DocTitle"]))
        story.append(Spacer(1, 0.8))
        story.append(Paragraph(meta_html, styles["MetaStyle"]))
        story.append(Spacer(1, 1.8))
        story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceBefore=0, spaceAfter=2.5))
        story.append(Paragraph("No roles matched your criteria.", styles["JobBody"]))
    else:
        for page_idx, page_jobs in enumerate(pages):
            page_num = page_idx + 1
            override = next((c.get("page_theme") for c in page_jobs if c.get("page_theme")), "")
            theme = override or _page_theme(page_jobs, page_num)

            for job in page_jobs:
                job["page"] = page_num
                job["page_theme"] = theme

            story.extend(_page_header(page_num, page_jobs, title_text, meta_html, styles))

            for job in page_jobs:
                story.append(_render_card(job, styles))
                story.append(Spacer(1, 2.2))

            if page_num == total_pages:
                story.append(Spacer(1, 0.8))
                story.append(playbook_table)
            else:
                story.append(PageBreak())

    doc.build(story)
    os.replace(temp_path, output_path)
    return total_pages
