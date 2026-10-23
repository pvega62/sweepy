from __future__ import annotations

import locale
import logging
import os
import shutil
from typing import Optional

from engine.docx import build_pdf_from_blocks, convert_docx_to_pdf, convert_with_word_bridge

log = logging.getLogger("sweepy.engine.documents")

TEXT_SUFFIXES = (".txt", ".text", ".md", ".markdown")
WORD_SUFFIXES = (".docx", ".doc")
CONVERTIBLE_SUFFIXES = (*WORD_SUFFIXES, *TEXT_SUFFIXES)
SUPPORTED_SUFFIXES = (*CONVERTIBLE_SUFFIXES, ".pdf")


class UnsupportedDocumentError(ValueError):
    """Raised when Sweepy holds no PDF conversion path for a file type."""


def _pdf_target(source_path: str, pdf_path: Optional[str]) -> str:
    """Return the resolved destination PDF path for ``source_path``."""
    if pdf_path:
        resolved = os.path.expanduser(pdf_path)
    else:
        resolved = os.path.splitext(source_path)[0] + ".pdf"
    return os.path.realpath(resolved)


def _read_text(path: str) -> str:
    """Read a text file as UTF-8, falling back to the local encoding."""
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return handle.read()
    except UnicodeDecodeError:
        encoding = locale.getpreferredencoding(False) or "utf-8"
        with open(path, "r", encoding=encoding, errors="replace") as handle:
            return handle.read()


def text_blocks(text: str) -> list[tuple[str, str]]:
    """Split plain text or Markdown into heading, bullet, and body blocks."""
    blocks: list[tuple[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            blocks.append(("heading", line.lstrip("#").strip()))
        elif line.startswith(("-", "*", "•")):
            blocks.append(("bullet", line.lstrip("-*•").strip()))
        else:
            blocks.append(("body", line))
    return blocks


def convert_to_pdf(source_path: str, pdf_path: Optional[str] = None) -> str:
    """Convert a document to PDF and return the resolved output path.

    ``.docx`` rebuilds clean text through python-docx and reportlab, then falls
    back to Microsoft Word. ``.doc`` uses the Word bridge directly. ``.txt`` and
    ``.md`` render as styled text. ``.pdf`` passes the source through, or copies
    it to an explicit ``pdf_path``. A blank ``pdf_path`` saves the PDF next to
    the source file.
    """
    resolved = os.path.realpath(os.path.expanduser(source_path))
    if not os.path.exists(resolved):
        raise FileNotFoundError(f"File not found: {source_path!r}")

    suffix = os.path.splitext(resolved)[1].lower()
    if suffix not in SUPPORTED_SUFFIXES:
        supported = ", ".join(SUPPORTED_SUFFIXES)
        raise UnsupportedDocumentError(
            f"Unsupported file type {suffix or '(none)'!r}. Sweepy converts: {supported}"
        )

    if suffix == ".docx":
        return convert_docx_to_pdf(resolved, pdf_path)

    if suffix == ".pdf":
        if not pdf_path:
            return resolved
        target = _pdf_target(resolved, pdf_path)
        if target == resolved:
            return resolved
        os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
        shutil.copyfile(resolved, target)
        log.info("Copied %s -> %s", resolved, target)
        return target

    target = _pdf_target(resolved, pdf_path)
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)

    if suffix == ".doc":
        try:
            convert_with_word_bridge(resolved, target)
        except Exception as exc:  # noqa: BLE001 - Microsoft Word is optional
            raise RuntimeError(
                f"Could not convert {resolved!r} to PDF. Legacy .doc files need "
                "Microsoft Word and the docx2pdf package; save the file as .docx "
                f"to convert it without Word. ({exc})"
            ) from exc
        log.info("Converted %s -> %s (docx2pdf / Microsoft Word)", resolved, target)
        return target

    blocks = text_blocks(_read_text(resolved))
    if not blocks:
        raise RuntimeError(f"The file holds no extractable text: {resolved!r}")
    build_pdf_from_blocks(
        blocks, target, title=os.path.splitext(os.path.basename(resolved))[0]
    )
    log.info("Converted %s -> %s (text)", resolved, target)
    return target
