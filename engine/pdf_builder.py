import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import inch

def format_compensation(job: dict) -> str:
    min_amt = job.get("min_amount") or 0
    max_amt = job.get("max_amount") or 0
    curr = job.get("currency", "USD")
    sym = "$" if curr == "USD" else curr + " "
    if min_amt and max_amt:
        return f"{sym}{int(min_amt):,} - {sym}{int(max_amt):,} / year"
    elif max_amt:
        return f"Up to {sym}{int(max_amt):,} / year"
    elif min_amt:
        return f"From {sym}{int(min_amt):,} / year"
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

    link_html = f"<a href='{url}' color='#2563EB'><u>{url[:45]}... [↗]</u></a>" if len(url) > 48 else f"<a href='{url}' color='#2563EB'><u>{url} [↗]</u></a>"

    lines = [
        Paragraph(f"<b>Rank: #{rank}</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b><font color='#047857'>{score}% MATCH</font></b>", styles['HeaderStyle']),
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

    story = []
    
    # Header Banner
    title_style = ParagraphStyle('MainTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=13, alignment=1, spaceAfter=2)
    story.append(Paragraph(f"Sweepy Directory — {profile_name}", title_style))
    story.append(Paragraph("Roles sorted by match score. Color badges indicate quick apply (Slate) vs custom responses (Amber).", ParagraphStyle('Sub', alignment=1, fontSize=8, textColor=colors.HexColor("#6B7280"), spaceAfter=6)))

    cards_on_page = 0
    total_pages = 1
    for i, job in enumerate(jobs):
        card = create_job_card(job, i + 1, styles)
        story.append(card)
        story.append(Spacer(1, 0.10 * inch))
        cards_on_page += 1

        if cards_on_page == 4 and i < len(jobs) - 1:
            story.append(PageBreak())
            cards_on_page = 0
            total_pages += 1

    doc.build(story)
    os.replace(temp_path, output_path)
    return total_pages
