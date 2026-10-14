from __future__ import annotations

import json
import os
from typing import Dict, List, Tuple

import pandas as pd
import pymupdf

PNG_DPI = 200

EXPORT_COLUMNS = [
    'rank',
    'match_value',
    'match_kind',
    'resume_track',
    'match_score',
    'badge',
    'unverified',
    'title',
    'company',
    'location',
    'platform',
    'domain',
    'min_amount',
    'max_amount',
    'currency',
    'comp',
    'benefits',
    'has_extended_response',
    'app_format',
    'url',
    'key_matches',
    'missing_skills',
    'playbook',
    'summary',
    'requirements',
    'alignment',
    'description'
]

def export_to_csv(jobs: List[Dict], output_path: str) -> Tuple[int, int]:
    if not jobs:
        return 0, 0

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    rows = []
    for j in jobs:
        row = dict(j)
        if isinstance(row.get('key_matches'), list):
            row['key_matches'] = ", ".join(row['key_matches'])
        if isinstance(row.get('missing_skills'), list):
            row['missing_skills'] = ", ".join(row['missing_skills'])
        rows.append(row)

    df = pd.DataFrame(rows)
    for col in EXPORT_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[EXPORT_COLUMNS]
    df.to_csv(output_path, index=False, encoding='utf-8')
    return len(df), len(df.columns)

def export_to_json(jobs: List[Dict], output_path: str):
    if not jobs:
        return
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)

def export_to_png(pdf_path: str, output_stem: str, dpi: int = PNG_DPI) -> List[str]:
    """Rasterize each page of a report PDF into a PNG image.

    A single-page PDF writes ``{output_stem}.png``; multi-page PDFs write
    ``{output_stem}_page{N}.png`` for each page. Returns the written paths.
    """
    os.makedirs(os.path.dirname(output_stem) or ".", exist_ok=True)
    paths: List[str] = []
    with pymupdf.open(pdf_path) as doc:
        total = doc.page_count
        for index, page in enumerate(doc):
            suffix = "" if total == 1 else f"_page{index + 1}"
            png_path = f"{output_stem}{suffix}.png"
            page.get_pixmap(dpi=dpi).save(png_path)
            paths.append(os.path.realpath(png_path))
    return paths
