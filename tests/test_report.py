import math
import os
import re

import pymupdf

from engine.exporter import export_to_png
from engine.pdf_builder import build_pdf, format_compensation
from engine.report import build_report, playbook_to_markup


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
        "concerns": "Concern text.",
        "comp": "$100K - $120K",
        "benefits": "Not disclosed",
        "page": 0,
        "page_theme": "",
    }


def _profile(cards_per_page=6, max_cards=24):
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
    assert pages == math.ceil(10 / 6) == 2


def test_format_compensation_keeps_hourly_unit():
    job = {"min_amount": 45, "max_amount": 55, "currency": "USD", "salary_period": "hour"}
    assert format_compensation(job) == "$45 - $55 / hour"


def test_format_compensation_collapses_equal_bounds():
    job = {"min_amount": 95000, "max_amount": 95000, "currency": "USD"}
    assert format_compensation(job) == "$95,000 / year"


def test_missing_cards_per_page_defaults_to_six(tmp_path):
    path = str(tmp_path / "r.pdf")
    profile = _profile()
    del profile["report"]["cards_per_page"]

    build_report([_card(i) for i in range(1, 11)], path, profile)

    assert [len(page[1]) for page in _pages(path)] == [6, 4]


def test_max_cards_truncates(tmp_path):
    path = str(tmp_path / "r.pdf")
    pages = build_report([_card(i) for i in range(1, 31)], path, _profile(max_cards=24))
    assert pages == 4


def test_max_cards_zero_means_unlimited(tmp_path):
    path = str(tmp_path / "r.pdf")
    pages = build_report([_card(i) for i in range(1, 31)], path, _profile(max_cards=0))
    assert pages == math.ceil(30 / 6) == 5


def test_links_per_page_matches_cards(tmp_path):
    path = str(tmp_path / "r.pdf")
    build_report([_card(i) for i in range(1, 11)], path, _profile())
    pages = _pages(path)
    assert len(pages) == 2
    assert len(pages[0][1]) == 6
    assert len(pages[1][1]) == 4


def test_long_cards_fit_without_overflowing_pages(tmp_path):
    cards = [_card(i) for i in range(1, 7)]
    long_text = (
        "Experienced technical communicator who creates clear product documentation, "
        "collaborates with engineering teams, and turns complex workflows into practical "
        "guides for users. "
    ) * 2
    for card in cards:
        card.update({
            "summary": long_text,
            "requirements": long_text,
            "alignment": long_text,
            "benefits": long_text,
        })

    path = str(tmp_path / "r.pdf")
    reported_pages = build_report(cards, path, _profile())
    pages = _pages(path)

    assert reported_pages == len(pages) == 2
    assert [len(page[1]) for page in pages] == [4, 2]
    assert all(card["page"] == 1 for card in cards[:4])
    assert all(card["page"] == 2 for card in cards[4:])


def test_legacy_pdf_uses_six_cards_when_they_fit(tmp_path):
    jobs = [
        {
            "title": f"Role {i}",
            "company": f"Company {i}",
            "location": "Remote",
            "match_score": 85,
            "url": f"https://jobs.example.com/{i}",
            "playbook": "Review details.",
            "key_matches": ["writing"],
            "missing_skills": [],
            "badge": "Slate",
        }
        for i in range(1, 11)
    ]
    path = str(tmp_path / "legacy.pdf")

    reported_pages = build_pdf(jobs, path, "Test")
    pages = _pages(path)

    assert reported_pages == len(pages) == 2
    assert [len(page[1]) for page in pages] == [6, 4]


def test_legacy_pdf_uses_fewer_cards_for_long_entries(tmp_path):
    long_text = (
        "Technical documentation experience across developer tools, APIs, "
        "and product workflows. "
    ) * 4
    jobs = [
        {
            "title": f"Senior Technical Writer {i}",
            "company": f"Company {i}",
            "location": "Remote - United States",
            "match_score": 85,
            "url": f"https://jobs.example.com/{i}",
            "playbook": long_text,
            "key_matches": [long_text],
            "missing_skills": [long_text],
            "badge": "Slate",
        }
        for i in range(1, 7)
    ]
    path = str(tmp_path / "legacy.pdf")

    reported_pages = build_pdf(jobs, path, "Test")
    pages = _pages(path)

    assert reported_pages == len(pages) == 2
    assert [len(page[1]) for page in pages] == [3, 3]


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


def test_card_renders_the_concern_next_to_the_highlight(tmp_path):
    path = str(tmp_path / "r.pdf")
    build_report([_card(1)], path, _profile(max_cards=1))
    text = _pages(path)[0][0]
    assert "Application Tip:" in text
    assert "Working Against You:" in text
    assert "Concern text." in text


def test_card_omits_the_concern_line_when_empty(tmp_path):
    card = _card(1)
    card["concerns"] = ""
    path = str(tmp_path / "r.pdf")
    build_report([card], path, _profile(max_cards=1))
    assert "Working Against You:" not in _pages(path)[0][0]


def test_card_renders_portfolio_fit_beside_the_match(tmp_path):
    card = _card(1, match_kind="match")
    card["portfolio_fit"] = 85
    path = str(tmp_path / "r.pdf")
    build_report([card], path, _profile(max_cards=1))
    text = _pages(path)[0][0]
    assert "89% MATCH" in text
    assert "85% PORTFOLIO FIT" in text
    assert text.index("89% MATCH") < text.index("85% PORTFOLIO FIT")


def test_card_omits_portfolio_fit_when_unset(tmp_path):
    path = str(tmp_path / "r.pdf")
    build_report([_card(1)], path, _profile(max_cards=1))
    text = _pages(path)[0][0]
    assert "PORTFOLIO FIT" in text  # the legend explains the score
    assert "% PORTFOLIO FIT" not in text  # but no card carries one


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
    assert cards[6]["page"] == 2
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
    assert len(paths) == 2
    assert [os.path.basename(p) for p in paths] == ["r_page1.png", "r_page2.png"]
    for path in paths:
        assert os.path.getsize(path) > 0


def test_playbook_to_markup_escapes_and_breaks_lines():
    markup = playbook_to_markup("R&D at Smith <LLP>\nSecond line")
    assert markup == "R&amp;D at Smith &lt;LLP&gt;<br/>Second line"


def test_playbook_to_markup_supports_bold_and_trims_blank_lines():
    markup = playbook_to_markup("\n**Apply first**\n\n")
    assert markup == "<b>Apply first</b>"


def test_playbook_to_markup_empty():
    assert playbook_to_markup("") == ""
    assert playbook_to_markup("   \n \n") == ""


def test_playbook_text_renders_literally(tmp_path):
    path = str(tmp_path / "r.pdf")
    build_report([_card(1)], path, _profile(max_cards=1), playbook="R&D at Smith <LLP>\nNext line")
    text = _pages(path)[-1][0]
    assert "R&D at Smith <LLP>" in text
    assert "Next line" in text


def test_playbook_reserves_space_only_on_the_last_page(tmp_path):
    path = str(tmp_path / "r.pdf")
    tall = "PROBE\n" + "\n".join(f"line {i}" for i in range(20))
    cards = [_card(i) for i in range(1, 25)]
    pages = build_report(cards, path, _profile(), playbook=tall)
    per_page = [len(re.findall(r"\d+% (?:MATCH|KEYWORD OVERLAP)", page[0])) for page in _pages(path)]
    assert pages == len(per_page)
    assert sum(per_page) == 24
    # Only the final page may leave room for the playbook box.
    assert per_page[:-1] == [6] * (len(per_page) - 1)


def _portfolio_card(i, **extra):
    card = _card(i)
    card.update(extra)
    return card


def test_card_lists_the_portfolio_pieces(tmp_path):
    path = str(tmp_path / "r.pdf")
    card = _portfolio_card(
        1,
        portfolio_url="https://example.com/work",
        portfolio_pieces=["Case Study A", "Case Study B"],
    )

    build_report([card], path, _profile())

    text = _pages(path)[0][0]
    assert "Portfolio:" in text
    assert "example.com" in text
    assert "Pieces: Case Study A, Case Study B" in text


def test_card_names_the_chosen_portfolio_highlight(tmp_path):
    path = str(tmp_path / "r.pdf")
    card = _portfolio_card(
        1,
        portfolio_url="https://example.com/work",
        portfolio_pieces=["Case Study A"],
        portfolio_highlight="Lead with Case Study A",
    )

    build_report([card], path, _profile())

    text = _pages(path)[0][0]
    assert "Highlight: Lead with Case Study A" in text
    assert "Pieces:" not in text


def test_card_names_a_local_portfolio_file(tmp_path):
    path = str(tmp_path / "r.pdf")
    card = _portfolio_card(1, portfolio_path=r"C:\work\portfolio.pdf")

    build_report([card], path, _profile())

    assert "Portfolio: portfolio.pdf" in _pages(path)[0][0]


def test_report_header_routes_each_track_to_its_portfolio(tmp_path):
    path = str(tmp_path / "r.pdf")
    profile = _profile()
    profile["portfolio"] = {
        "sources": [
            {"track": "Tech Writer Resume", "url": "https://example.com/tech"},
        ]
    }

    build_report([_card(1)], path, profile)

    text = _pages(path)[0][0]
    assert "Portfolio Routing:" in text
    assert "Tech Writer Resume" in text
    assert "example.com/tech" in text


def test_report_omits_portfolio_rows_without_a_portfolio(tmp_path):
    path = str(tmp_path / "r.pdf")

    build_report([_card(1)], path, _profile())

    text = _pages(path)[0][0]
    assert "Portfolio Routing" not in text
    assert "Portfolio:" not in text
    assert "PORTFOLIO SOURCES" not in text


def test_default_playbook_names_the_portfolio_sources(tmp_path):
    path = str(tmp_path / "r.pdf")
    profile = _profile()
    profile["portfolio"] = {"sources": [{"url": "https://example.com/work"}]}
    card = _portfolio_card(1, portfolio_highlight="Case Study A")

    build_report([card], path, profile)

    text = _pages(path)[-1][0]
    assert "PORTFOLIO SOURCES" in text
    assert "example.com/work" in text
    assert "1 role(s) name the pieces to highlight" in text
