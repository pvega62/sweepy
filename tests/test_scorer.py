import pymupdf

from engine.scorer import determine_badge, extract_resume_keywords, score_jobs


def _job(title, desc, url="http://example.com/job"):
    return {"title": title, "company": "Acme", "location": "NYC", "description": desc, "url": url}


def test_zero_keyword_job_scores_zero():
    jobs = [_job("Generic", "generic responsibilities and duties")]
    scored, _ = score_jobs(jobs, "", ["python", "react", "sql"], 1.0)
    assert scored[0]["match_score"] == 0


def test_monotonicity_more_matches_scores_higher():
    skills = ["python", "react", "sql"]
    low = _job("Low", "react experience")
    high = _job("High", "python react sql experience")
    scored, _ = score_jobs([low, high], "", skills, 1.0)
    by_title = {j["title"]: j["match_score"] for j in scored}
    assert by_title["High"] > by_title["Low"]
    assert by_title["Low"] > 0


def test_non_tech_domain_fixture():
    skills = ["patient care", "HIPAA", "medication administration"]
    jobs = [
        _job("RN", "provide patient care and administer medication"),
        _job("CNA", "assist with daily living"),
    ]
    scored, _ = score_jobs(jobs, "", skills, 1.0)
    by_title = {j["title"]: j["match_score"] for j in scored}
    assert by_title["RN"] >= by_title["CNA"]


def test_determine_badge():
    assert determine_badge("requires a cover letter") == "Amber"
    assert determine_badge("standard application") == "Slate"
    assert determine_badge("") == "Slate"


def _make_resume_pdf(path):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Python React SQL Westlaw")
    doc.save(str(path))
    doc.close()


def test_extract_resume_keywords_from_pdf(tmp_path):
    pdf = tmp_path / "resume.pdf"
    _make_resume_pdf(pdf)
    kw = extract_resume_keywords(str(pdf), [])
    assert "Python" in kw
    assert "SQL" in kw
