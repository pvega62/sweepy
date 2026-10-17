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
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = docx.Document(docx_path)

    def classify_paragraph(para: Paragraph) -> Optional[tuple[str, str]]:
        text = para.text.strip()
        if not text:
            return None
        style_name = (para.style.name or "").lower() if para.style is not None else ""
        if para.style is not None and style_name.startswith(("heading", "title")):
            return ("heading", text)
        if style_name.startswith(("list", "bullet")) or text.startswith(("•", "-", "*")):
            return ("bullet", text.lstrip("•-* ").strip())
        return ("body", text)

    blocks: list[tuple[str, str]] = []
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            block = classify_paragraph(Paragraph(child, document))
            if block is not None:
                blocks.append(block)
        elif child.tag == qn("w:tbl"):
            try:
                table = Table(child, document)
            except Exception:  # noqa: BLE001 - skip malformed tables
                continue
            for row in table.rows:
                try:
                    cells = row.cells
                except Exception:  # noqa: BLE001 - skip malformed rows
                    continue
                for cell in cells:
                    try:
                        text = cell.text.strip()
                    except Exception:  # noqa: BLE001 - skip malformed cells
                        continue
                    if not text:
                        continue
                    if text.startswith(("•", "-", "*")):
                        blocks.append(("bullet", text.lstrip("•-* ").strip()))
                    else:
                        blocks.append(("body", text))
    return blocks


def docx_text(docx_path: str) -> str:
    """Return the plain text of a DOCX, one paragraph or table cell per line.

    Shares ``_read_docx_blocks`` with the PDF builder, so text extraction and
    conversion always agree on what a DOCX contains. Raises ImportError when
    python-docx is not installed.
    """
    return "\n".join(text for _, text in _read_docx_blocks(docx_path))


def build_pdf_from_blocks(
    blocks: list[tuple[str, str]], pdf_path: str, title: str = ""
) -> None:
    """Render ``(kind, text)`` blocks into a clean single-column PDF.

    ``kind`` is one of ``heading``, ``bullet``, or ``body``. The DOCX and the
    plain-text converters share this builder, so every source renders alike.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

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
        title=title,
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


def _convert_with_python_docx(docx_path: str, pdf_path: str) -> None:
    """Rebuild a clean single-column PDF from DOCX text with reportlab."""
    blocks = _read_docx_blocks(docx_path)
    if not blocks:
        raise RuntimeError("The DOCX contains no extractable text.")
    build_pdf_from_blocks(
        blocks, pdf_path, title=os.path.splitext(os.path.basename(docx_path))[0]
    )


def convert_with_word_bridge(source_path: str, pdf_path: str) -> None:
    """Render a Word document through Microsoft Word via the docx2pdf COM bridge."""
    from docx2pdf import convert  # optional: requires Word on Windows

    convert(source_path, pdf_path)


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
        convert_with_word_bridge(resolved_docx, resolved_pdf)
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
