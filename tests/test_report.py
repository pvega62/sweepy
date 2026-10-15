import math
import os

import pymupdf

from engine.exporter import export_to_png
from engine.report import build_report


def _card(i, match_kind="overlap", extended=False):
    return {
        "id": f"id{i}",
        "rank": i,
        "title": f"Title {i}",
        "company": f"Company {i}",
        "platform": "Ashby",
        "url": f"https://jobs.ashbyhq.com/org/{i}",
        "location": "Remote - US",
        "match_value": 90 - i,
        "match_kind": match_kind,
        "resume_track": "Tech Writer Resume",
        "resume_color": "#1D4ED8",
        "has_extended_response": extended,
        "app_format": "Standard Application (Resume upload and standard candidate profile).",
        "domain": "Cloud Compute",
        "summary": "Summary text.",
        "requirements": "Requirements text.",
        "alignment": "Alignment text.",
        "comp": "$100K - $120K",
        "benefits": "Not disclosed",
        "page": 0,
        "page_theme": "",
    }


def _profile(cards_per_page=4, max_cards=24):
    return {
        "name": "Test User",
        "search": {"titles": ["Technical Writer"], "location": "NYC"},
        "resume": {"tracks": [{"name": "Tech Writer Resume", "color": "#1D4ED8", "route_keywords": []}]},
        "report": {"cards_per_page": cards_per_page, "max_cards": max_cards},
    }


def _pages(path):
    doc = pymupdf.open(path)
    try:
        result = [(page.get_text(), [link for link in page.get_links()]) for page in doc]
    finally:
        doc.close()
    return result


def test_page_count_is_dynamic(tmp_path):
    path = str(tmp_path / "r.pdf")
    pages = build_report([_card(i) for i in range(1, 11)], path, _profile())
    assert pages == math.ceil(10 / 4) == 3


def test_max_cards_truncates(tmp_path):
    path = str(tmp_path / "r.pdf")
    pages = build_report([_card(i) for i in range(1, 31)], path, _profile(max_cards=24))
    assert pages == 6


def test_max_cards_zero_means_unlimited(tmp_path):
    path = str(tmp_path / "r.pdf")
    pages = build_report([_card(i) for i in range(1, 31)], path, _profile(max_cards=0))
    assert pages == math.ceil(30 / 4) == 8


def test_links_per_page_matches_cards(tmp_path):
    path = str(tmp_path / "r.pdf")
    build_report([_card(i) for i in range(1, 11)], path, _profile())
    pages = _pages(path)
    assert len(pages) == 3
    assert len(pages[0][1]) == 4
    assert len(pages[1][1]) == 4
    assert len(pages[2][1]) == 2


def test_provenance_label_overlap_vs_match(tmp_path):
    path = str(tmp_path / "r.pdf")
    build_report(
        [_card(1, match_kind="overlap"), _card(2, match_kind="match")],
        path,
        _profile(max_cards=2),
    )
    pages = _pages(path)
    text = pages[0][0]
    assert "KEYWORD OVERLAP" in text
    assert "MATCH" in text


def test_amber_and_slate_cards(tmp_path):
    path = str(tmp_path / "r.pdf")
    build_report([_card(1, extended=True), _card(2, extended=False)], path, _profile(max_cards=2))
    text = _pages(path)[0][0]
    assert "EXTENDED RESPONSES REQUIRED" in text
    assert "STANDARD / QUICK APPLY" in text


def test_playbook_on_last_page(tmp_path):
    path = str(tmp_path / "r.pdf")
    build_report([_card(i) for i in range(1, 6)], path, _profile())
    pages = _pages(path)
    assert "PLAYBOOK" in pages[-1][0]


def test_zero_jobs_produces_one_page(tmp_path):
    path = str(tmp_path / "r.pdf")
    pages = build_report([], path, _profile())
    assert pages == 1
    text = _pages(path)[0][0]
    assert "No roles matched" in text


def test_build_report_sets_page_fields(tmp_path):
    cards = [_card(i) for i in range(1, 10)]
    path = str(tmp_path / "r.pdf")
    build_report(cards, path, _profile())
    assert cards[0]["page"] == 1
    assert cards[4]["page"] == 2
    assert cards[0]["page_theme"].startswith("Page 1")


def test_export_to_png_single_page_stem(tmp_path):
    pdf = str(tmp_path / "r.pdf")
    build_report([_card(1), _card(2)], pdf, _profile(max_cards=2))
    paths = export_to_png(pdf, str(tmp_path / "r"))
    assert paths == [os.path.realpath(str(tmp_path / "r.png"))]
    with open(paths[0], "rb") as f:
        assert f.read(8) == b"\x89PNG\r\n\x1a\n"


def test_export_to_png_writes_one_image_per_page(tmp_path):
    pdf = str(tmp_path / "r.pdf")
    build_report([_card(i) for i in range(1, 11)], pdf, _profile())
    paths = export_to_png(pdf, str(tmp_path / "r"))
    assert len(paths) == 3
    assert [os.path.basename(p) for p in paths] == ["r_page1.png", "r_page2.png", "r_page3.png"]
    for path in paths:
        assert os.path.getsize(path) > 0
