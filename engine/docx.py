from __future__ import annotations

import logging
import os
from typing import Optional

log = logging.getLogger("sweepy.engine.docx")


def _read_docx_blocks(docx_path: str) -> list[tuple[str, str]]:
    """Extract (style, text) blocks from a DOCX using python-docx.

    The returned style is one of ``heading``, ``bullet``, or ``body`` so the
    PDF builder can approximate the source layout without Microsoft Word.
    """
    import docx  # python-docx

    document = docx.Document(docx_path)
    blocks: list[tuple[str, str]] = []
    for para in document.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style_name = (para.style.name or "").lower() if para.style is not None else ""
        if para.style is not None and style_name.startswith(("heading", "title")):
            blocks.append(("heading", text))
        elif style_name.startswith(("list", "bullet")) or text.startswith(("•", "-", "*")):
            blocks.append(("bullet", text.lstrip("•-* ").strip()))
        else:
            blocks.append(("body", text))
    return blocks


def _convert_with_python_docx(docx_path: str, pdf_path: str) -> None:
    """Rebuild a clean single-column PDF from DOCX text with reportlab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    blocks = _read_docx_blocks(docx_path)
    if not blocks:
        raise RuntimeError("The DOCX contains no extractable text.")

    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle(
        "DocxHeading",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "DocxBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        spaceAfter=4,
    )
    bullet_style = ParagraphStyle(
        "DocxBullet",
        parent=body_style,
        leftIndent=18,
        bulletIndent=6,
    )

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
        title=os.path.splitext(os.path.basename(docx_path))[0],
    )

    story = []
    for kind, text in blocks:
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if kind == "heading":
            story.append(Paragraph(escaped, heading_style))
        elif kind == "bullet":
            story.append(Paragraph(escaped, bullet_style, bulletText="•"))
        else:
            story.append(Paragraph(escaped, body_style))
        story.append(Spacer(1, 2))

    doc.build(story)


def _convert_with_docx2pdf(docx_path: str, pdf_path: str) -> None:
    """Render the DOCX through Microsoft Word via the docx2pdf COM bridge."""
    from docx2pdf import convert  # optional: requires Word on Windows

    convert(docx_path, pdf_path)


def _pdf_target(docx_path: str, pdf_path: Optional[str]) -> str:
    if pdf_path:
        resolved = os.path.expanduser(pdf_path)
    else:
        resolved = os.path.splitext(docx_path)[0] + ".pdf"
    return os.path.realpath(resolved)


def convert_docx_to_pdf(docx_path: str, pdf_path: Optional[str] = None) -> str:
    """Convert a DOCX file to PDF.

    The primary path rebuilds a clean PDF from DOCX text using python-docx and
    reportlab, so it runs anywhere. When that fails, Sweepy falls back to
    docx2pdf, which renders through Microsoft Word for pixel-faithful output on
    Windows. A blank ``pdf_path`` saves the PDF next to the source DOCX.

    Returns the resolved output PDF path.
    """
    resolved_docx = os.path.realpath(os.path.expanduser(docx_path))
    if not os.path.exists(resolved_docx):
        raise FileNotFoundError(f"DOCX file not found: {docx_path!r}")
    if not resolved_docx.lower().endswith(".docx"):
        raise ValueError(f"Expected a .docx file, got: {docx_path!r}")

    resolved_pdf = _pdf_target(resolved_docx, pdf_path)
    os.makedirs(os.path.dirname(resolved_pdf) or ".", exist_ok=True)

    errors: list[str] = []

    try:
        _convert_with_python_docx(resolved_docx, resolved_pdf)
        log.info("Converted %s -> %s (python-docx + reportlab)", resolved_docx, resolved_pdf)
        return resolved_pdf
    except Exception as exc:  # noqa: BLE001 - fall back to the Word bridge
        errors.append(f"python-docx: {exc}")

    try:
        _convert_with_docx2pdf(resolved_docx, resolved_pdf)
        log.info("Converted %s -> %s (docx2pdf / Microsoft Word)", resolved_docx, resolved_pdf)
        return resolved_pdf
    except Exception as exc:  # noqa: BLE001 - surface a combined error
        errors.append(f"docx2pdf: {exc}")

    raise RuntimeError(
        f"Could not convert {resolved_docx!r} to PDF. " + " | ".join(errors)
    )


def safe_pdf_name(docx_path: str, pdf_path: Optional[str] = None) -> str:
    """Return the output PDF path without writing it (used by the MCP tool)."""
    return _pdf_target(os.path.realpath(os.path.expanduser(docx_path)), pdf_path)
