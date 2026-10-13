import engine.config as cfg
from engine.config import _parse_salary, load_config, save_profile


def test_parse_salary():
    assert _parse_salary("65000") == 65000
    assert _parse_salary("65,000") == 65000
    assert _parse_salary("$65,000") == 65000
    assert _parse_salary("65k") == 65000
    assert _parse_salary("") == 0
    assert _parse_salary("-500") is None
    assert _parse_salary("abc") is None


def test_save_load_roundtrip(tmp_path):
    profile = {"name": "X", "search": {"titles": ["T"], "remote_only": True, "min_salary": 5}}
    path = save_profile(profile, str(tmp_path / "p.yaml"))
    assert load_config(path) == profile


def _stub(answer):
    return type("Q", (), {"ask": lambda self: answer})()


def _install_wizard_stubs(monkeypatch, texts, confirms, checkboxes):
    monkeypatch.setattr(cfg.questionary, "text", lambda *a, **k: _stub(next(texts)))
    monkeypatch.setattr(cfg.questionary, "confirm", lambda *a, **k: _stub(next(confirms)))
    monkeypatch.setattr(cfg.questionary, "checkbox", lambda *a, **k: _stub(next(checkboxes)))


def test_wizard_writes_remote_only_and_parses_salary(monkeypatch, tmp_path):
    texts = iter(["Alice", "Writer, Editor", "NYC", "resume.pdf", "65,000", ""])
    confirms = iter([True, True, False, False])
    checkboxes = iter([["greenhouse", "ashby"], ["pdf", "csv"]])
    _install_wizard_stubs(monkeypatch, texts, confirms, checkboxes)
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard()
    data = load_config(path)

    assert data["search"]["remote_only"] is True
    assert data["search"]["include_hybrid"] is True
    assert data["search"]["min_salary"] == 65000


def test_wizard_reparses_invalid_salary(monkeypatch, tmp_path):
    texts = iter(["Alice", "Writer", "NYC", "resume.pdf", "abc", "65k", ""])
    confirms = iter([False, True, False, False])
    checkboxes = iter([["greenhouse"], ["pdf"]])
    _install_wizard_stubs(monkeypatch, texts, confirms, checkboxes)
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard()
    data = load_config(path)

    assert data["search"]["min_salary"] == 65000
