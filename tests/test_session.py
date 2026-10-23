import hashlib
import threading

import pytest

from engine.session import SweepSession, stable_id


def _card(i, url=None):
    return {
        "id": f"id{i}",
        "rank": i,
        "title": f"T{i}",
        "url": url or f"https://example.com/job/{i}",
        "match_value": 90 - i,
        "match_kind": "overlap",
    }


def test_stable_id_deterministic():
    assert stable_id("https://example.com/job/1") == stable_id("https://example.com/job/1")
    assert stable_id("a") != stable_id("b")


def test_stable_id_matches_sha1():
    assert stable_id("x") == hashlib.sha1(b"x").hexdigest()


def test_upsert_and_all_preserve_order():
    s = SweepSession()
    s.upsert(_card(1))
    s.upsert(_card(2))
    assert [c["id"] for c in s.all()] == ["id1", "id2"]


def test_later_upsert_wins():
    s = SweepSession()
    s.upsert(_card(1))
    s.upsert({"id": "id1", "match_value": 55, "match_kind": "match"})
    assert s.get("id1")["match_value"] == 55
    assert s.get("id1")["match_kind"] == "match"


def test_upsert_fills_missing_id_from_url():
    s = SweepSession()
    s.upsert({"url": "https://example.com/job/9", "title": "T"})
    assert s.get(stable_id("https://example.com/job/9"))["title"] == "T"


def test_apply_judgments_merges_non_none():
    s = SweepSession()
    s.upsert(_card(1))
    card = s.apply_judgments("id1", match_value=99, match_kind="match", summary=None)
    assert card["match_value"] == 99
    assert card["match_kind"] == "match"
    assert card["title"] == "T1"


def test_apply_judgments_missing_key():
    s = SweepSession()
    with pytest.raises(KeyError):
        s.apply_judgments("nope", match_value=1)


def test_judgment_reranks_by_assessed_score():
    s = SweepSession()
    for i in (1, 2, 3):
        s.upsert(_card(i))
    s.apply_judgments("id3", match_value=99, match_kind="match")
    assert [c["id"] for c in s.all()] == ["id3", "id1", "id2"]
    assert [c["rank"] for c in s.all()] == [1, 2, 3]


def test_judgment_without_score_leaves_rank_alone():
    s = SweepSession()
    for i in (1, 2):
        s.upsert(_card(i))
    card = s.apply_judgments("id2", domain="Litigation")
    assert card["rank"] == 2
    assert [c["id"] for c in s.all()] == ["id1", "id2"]


def test_judgment_clears_derived_page_labels():
    s = SweepSession()
    card = _card(1)
    card.update({"page": 1, "page_theme": "Page 1: Ranks 1-6"})
    s.upsert(card)
    judged = s.apply_judgments("id1", match_value=70)
    assert "page" not in judged
    assert "page_theme" not in judged


def test_ties_keep_previous_order():
    s = SweepSession()
    for i in (1, 2, 3):
        s.upsert(_card(i))
    s.apply_judgments("id3", match_value=89)
    assert [c["id"] for c in s.all()] == ["id1", "id3", "id2"]


def test_save_load_roundtrip(tmp_path):
    s = SweepSession()
    s.upsert(_card(1))
    s.upsert(_card(2))
    path = tmp_path / "session.json"
    s.save(str(path))
    loaded = SweepSession.load(str(path))
    assert [c["id"] for c in loaded.all()] == ["id1", "id2"]


def test_load_missing_file_returns_empty():
    assert SweepSession.load("does/not/exist.json").all() == []


def test_thread_safe_upsert():
    s = SweepSession()

    def add(i):
        for _ in range(100):
            s.upsert(_card(i))

    threads = [threading.Thread(target=add, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(s.all()) == 4
