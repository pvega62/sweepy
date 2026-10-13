from __future__ import annotations

import json
import os
from typing import Dict, List, Tuple

import pandas as pd

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
