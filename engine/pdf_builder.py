import os
from io import BytesIO
from xml.sax.saxutils import escape as _xml_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def format_compensation(job: dict) -> str:
    min_amt = job.get("min_amount") or 0
    max_amt = job.get("max_amount") or 0
    curr = job.get("currency", "USD")
    sym = "$" if curr == "USD" else curr + " "
    period = str(job.get("salary_period") or "year").lower()
    unit = {"hour": "/ hour", "day": "/ day", "week": "/ week", "month": "/ month"}.get(period, "/ year")
    if min_amt and max_amt and min_amt != max_amt:
        return f"{sym}{int(min_amt):,} - {sym}{int(max_amt):,} {unit}"
    elif max_amt and not min_amt:
        return f"Up to {sym}{int(max_amt):,} {unit}"
    elif min_amt and not max_amt:
        return f"From {sym}{int(min_amt):,} {unit}"
    elif min_amt and max_amt:
        return f"{sym}{int(min_amt):,} {unit}"
    return "Competitive / Not Disclosed"

def create_job_card(job: dict, rank: int, styles: dict) -> Table:
    title = job.get("title", "Untitled Role")
    company = job.get("company", "Company")
    location = job.get("location", "Location Not Specified")
    score = job.get("match_score", 0)
    badge = job.get("badge", "Slate")
    url = job.get("url", "#")
    platform = job.get("platform", "Direct")
    
    key_matches = ", ".join(job.get("key_matches", [])) or "General background"
    missing = ", ".join(job.get("missing_skills", [])) or "None identified"
    playbook = job.get("playbook", "Review job details carefully.")
    comp_str = format_compensation(job)

    if badge == "Amber":
        bg_color = colors.HexColor("#FFFBEB")
        border_color = colors.HexColor("#F59E0B")
        badge_html = "<font color='#B45309'><b>[EXTENDED RESPONSES REQUIRED - AMBER]</b></font>"
    else:
        bg_color = colors.HexColor("#F9FAFB")
        border_color = colors.HexColor("#D1D5DB")
        badge_html = "<font color='#4B5563'><b>[STANDARD / QUICK APPLY - SLATE]</b></font>"

    link_href = _xml_escape(url)
    link_text = _xml_escape(url[:45] + "..." if len(url) > 48 else url)
    link_html = f"<a href='{link_href}' color='#2563EB'><u>{link_text} [↗]</u></a>"

    if score < 30:
        score_html = f"<font color='#B45309'><b>{score}% MATCH (Low match)</b></font>"
    else:
        score_html = f"<font color='#047857'><b>{score}% MATCH</b></font>"

    lines = [
        Paragraph(f"<b>Rank: #{rank}</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {score_html}", styles['HeaderStyle']),
        Paragraph(f"<b>Role:</b> {title}", styles['BodyBold']),
        Paragraph(f"<b>Company:</b> {company} &nbsp;|&nbsp; <b>Location:</b> {location} ({platform})", styles['BodyStyle']),
        Paragraph(f"<b>Compensation:</b> {comp_str}", styles['BodyStyle']),
        Paragraph(f"<b>Key Matches:</b> {key_matches} &nbsp;|&nbsp; <b>Missing:</b> {missing}", styles['SmallStyle']),
        Paragraph(f"<b>Playbook:</b> {playbook}", styles['PlaybookStyle']),
        Paragraph(f"<b>Apply:</b> {link_html} &nbsp;&nbsp; {badge_html}", styles['SmallStyle'])
    ]

    card = Table([[lines]], colWidths=[7.2 * inch])
    card.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_color),
        ('BOX', (0, 0), (-1, -1), 1.2, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    return card

def build_pdf(jobs: list, output_path: str, profile_name: str) -> int:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    temp_path = output_path + ".tmp.pdf"

    doc = SimpleDocTemplate(
        temp_path,
        pagesize=letter,
        rightMargin=0.4 * inch,
        leftMargin=0.4 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.4 * inch
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor("#111827"), spaceAfter=2))
    styles.add(ParagraphStyle('BodyBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9.5, textColor=colors.HexColor("#1F2937"), spaceAfter=1))
    styles.add(ParagraphStyle('BodyStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor("#374151"), spaceAfter=1))
    styles.add(ParagraphStyle('SmallStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8, textColor=colors.HexColor("#4B5563"), spaceAfter=1))
    styles.add(ParagraphStyle('PlaybookStyle', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=8, textColor=colors.HexColor("#1E40AF"), spaceAfter=2))

    # Header Banner
    title_style = ParagraphStyle('MainTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=13, alignment=1, spaceAfter=2)
    header = [
        Paragraph(f"Sweepy Directory — {profile_name}", title_style),
        Paragraph(
            "Roles sorted by match score. Color badges indicate quick apply (Slate) vs custom responses (Amber).",
            ParagraphStyle(
                'Sub', alignment=1, fontSize=8,
                textColor=colors.HexColor("#6B7280"), spaceAfter=6,
            ),
        ),
    ]
    measurement_canvas = Canvas(BytesIO(), pagesize=letter)

    def flowable_height(flowable):
        _, height = flowable.wrapOn(measurement_canvas, doc.width, doc.height)
        return height + flowable.getSpaceBefore() + flowable.getSpaceAfter()

    card_blocks = [
        (create_job_card(job, i + 1, styles), Spacer(1, 0.10 * inch))
        for i, job in enumerate(jobs)
    ]
    pages = []
    next_card = 0
    while next_card < len(card_blocks):
        page_jobs = []
        used_height = (
            sum(flowable_height(item) for item in header)
            if not pages else 0
        )
        while next_card + len(page_jobs) < len(card_blocks) and len(page_jobs) < 6:
            card, gap = card_blocks[next_card + len(page_jobs)]
            card_height = flowable_height(card) + flowable_height(gap)
            if page_jobs and used_height + card_height > doc.height:
                break
            page_jobs.append(card_blocks[next_card + len(page_jobs)])
            used_height += card_height
        pages.append(page_jobs)
        next_card += len(page_jobs)

    story = []
    if not pages:
        story.extend(header)
    for page_num, page_jobs in enumerate(pages):
        if page_num == 0:
            story.extend(header)
        for card, gap in page_jobs:
            story.extend((card, gap))
        if page_num < len(pages) - 1:
            story.append(PageBreak())

    doc.build(story)
    os.replace(temp_path, output_path)
    return max(1, len(pages))
