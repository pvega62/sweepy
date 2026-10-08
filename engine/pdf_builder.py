import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch

def get_styles():
    styles = getSampleStyleSheet()
    
    # Custom styles
    styles.add(ParagraphStyle(
        name='CardTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        spaceAfter=4,
        textColor=colors.HexColor("#111827")
    ))
    
    styles.add(ParagraphStyle(
        name='CardCompany',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.HexColor("#3B82F6"),
        spaceAfter=4
    ))
    
    styles.add(ParagraphStyle(
        name='CardDetails',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor("#4B5563")
    ))
    
    return styles

def create_job_card(job: dict, rank: int, styles: dict):
    """
    Creates a ReportLab Table representing a single job card.
    """
    title = job.get('title', 'Unknown Title')
    company = job.get('company', 'Unknown Company')
    location = job.get('location', 'Remote / Unknown')
    score = job.get('match_score', 0)
    badge = job.get('badge', 'Slate')
    url = job.get('url', '#')
    
    # Determine colors based on Badge (Amber = Extended Response, Slate = Standard)
    if badge == "Amber":
        bg_color = colors.HexColor("#FFFBEB")
        border_color = colors.HexColor("#F59E0B")
        badge_text = "<font color='#B45309'><b>[EXTENDED RESPONSES REQUIRED]</b></font>"
    else:
        bg_color = colors.white
        border_color = colors.HexColor("#D1D5DB")
        badge_text = "<font color='#6B7280'>[STANDARD QUICK APPLY]</font>"
        
    # Card Content
    content = [
        Paragraph(f"#{rank} - {title} &nbsp;&nbsp;&nbsp; <b>{score}% Match</b>", styles['CardTitle']),
        Paragraph(f"<b><a href='{url}' color='blue'>{company}</a></b>", styles['CardCompany']),
        Paragraph(f"{location} &nbsp;|&nbsp; {badge_text}", styles['CardDetails'])
    ]
    
    # Wrap in a Table for the border and background
    # We use a 1x1 table to act as the "card" container
    card = Table([[content]], colWidths=[6.5 * inch])
    card.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_color),
        ('BOX', (0, 0), (-1, -1), 1.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    return card

def build_pdf(jobs: list, output_path: str, profile_name: str):
    """
    Generate a PDF report with exactly 4 job cards per page.
    Uses an atomic write strategy to prevent file locks.
    """
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    temp_path = output_path + ".tmp.pdf"
    
    doc = SimpleDocTemplate(
        temp_path,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch
    )
    
    styles = get_styles()
    story = []
    
    # Header
    title_style = ParagraphStyle(
        'MainTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=colors.HexColor("#1F2937"),
        alignment=1, # Center
        spaceAfter=12
    )
    
    story.append(Paragraph(f"Career Sweep Report: {profile_name}", title_style))
    story.append(Paragraph("Jobs are sorted by Match Percentage against your must-have skills.", styles['Normal']))
    story.append(Spacer(1, 0.25 * inch))
    
    # Add Cards (4 per page)
    cards_on_page = 0
    for i, job in enumerate(jobs):
        card = create_job_card(job, i + 1, styles)
        story.append(card)
        story.append(Spacer(1, 0.15 * inch))
        
        cards_on_page += 1
        
        # After 4 cards, force a page break
        if cards_on_page == 4 and i < len(jobs) - 1:
            from reportlab.platypus import PageBreak
            story.append(PageBreak())
            cards_on_page = 0

    try:
        doc.build(story)
        # Atomic replacement for Windows safety (user rule)
        os.replace(temp_path, output_path)
        print(f"PDF successfully generated at: {output_path}")
    except Exception as e:
        print(f"Error building PDF: {e}")
        if os.path.exists(temp_path):
             os.remove(temp_path)
