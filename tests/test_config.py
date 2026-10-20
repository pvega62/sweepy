import logging
import os
from types import SimpleNamespace

import pytest
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.output import DummyOutput

import engine.config as cfg
from engine.config import _parse_salary, is_valid_color, load_config, save_profile


def test_parse_salary():
    assert _parse_salary("65000") == 65000
    assert _parse_salary("65,000") == 65000
    assert _parse_salary("$65,000") == 65000
    assert _parse_salary("65k") == 65000
    assert _parse_salary("") == 0
    assert _parse_salary("-500") is None
    assert _parse_salary("abc") is None
    assert _parse_salary("inf") is None
    assert _parse_salary("infinityk") is None


def test_is_valid_color():
    assert is_valid_color("#1D4ED8") is True
    assert is_valid_color("#fff") is True
    assert is_valid_color("#GGGGGG") is False
    assert is_valid_color("navy") is True
    assert is_valid_color("Navy") is True
    assert is_valid_color("notacolor") is False
    assert is_valid_color("") is False


def test_save_load_roundtrip(tmp_path):
    profile = {"name": "X", "search": {"titles": ["T"], "remote_only": True, "min_salary": 5}}
    path = save_profile(profile, str(tmp_path / "p.yaml"))
    assert load_config(path) == profile


@pytest.mark.parametrize("yaml_text", ["", "- item\n", "42\n"])
def test_load_config_rejects_non_mapping_yaml(tmp_path, yaml_text):
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml_text, encoding="utf-8")

    with pytest.raises(ValueError, match="must contain a YAML mapping"):
        load_config(str(path))


def test_ask_tab_accepts_text_select_and_checkbox_values():
    with create_pipe_input() as pipe_input:
        question = cfg.questionary.text(
            "Name", input=pipe_input, output=DummyOutput()
        )
        pipe_input.send_text("Alice\t")
        assert cfg._ask(question) == "Alice"

    with create_pipe_input() as pipe_input:
        question = cfg.questionary.select(
            "Action", choices=["Submit", "Edit"], input=pipe_input, output=DummyOutput()
        )
        pipe_input.send_text("\t")
        assert cfg._ask(question) == "Submit"

    with create_pipe_input() as pipe_input:
        question = cfg.questionary.checkbox(
            "Formats", choices=["PDF", "CSV"], input=pipe_input, output=DummyOutput()
        )
        pipe_input.send_text("\t")
        assert cfg._ask(question) == []


def test_ask_escape_goes_back_and_arrow_navigation_still_works():
    with create_pipe_input() as pipe_input:
        question = cfg.questionary.text(
            "Name", input=pipe_input, output=DummyOutput()
        )
        pipe_input.send_bytes(b"\x1b")
        with pytest.raises(cfg._GoBack):
            cfg._ask(question)

    with create_pipe_input() as pipe_input:
        question = cfg.questionary.select(
            "Action", choices=["Submit", "Edit"], input=pipe_input, output=DummyOutput()
        )
        pipe_input.send_bytes(b"\x1b[B\r")
        assert cfg._ask(question) == "Edit"


def test_wizard_escape_returns_to_launchpad_without_saving(monkeypatch):
    def ask_name(current=None):
        with create_pipe_input() as pipe_input:
            question = cfg.questionary.text(
                "Name", input=pipe_input, output=DummyOutput()
            )
            pipe_input.send_bytes(b"\x1b")
            return cfg._ask(question)

    monkeypatch.setattr(
        cfg, "_build_steps", lambda: [cfg._Step("name", "Name", ask_name)]
    )
    selects = iter(["Create a new profile", "Exit"])
    monkeypatch.setattr(
        cfg, "_wizard_menu_select", lambda profile_data=None: _stub(next(selects))
    )
    monkeypatch.setattr(
        cfg, "save_profile", lambda *args, **kwargs: pytest.fail("profile was saved")
    )

    assert cfg.run_wizard() is None


def _stub(answer):
    application = type("App", (), {"key_bindings": KeyBindings()})()
    return SimpleNamespace(
        application=application,
        ask=lambda: answer,
        unsafe_ask=lambda: answer,
    )


def _default_selects():
    """Drive the main menu, then the review screen, then exit."""
    yield "Create a new profile"
    yield "Submit profile"
    while True:
        yield "Exit"


def _install_wizard_stubs(monkeypatch, texts, confirms, checkboxes, selects=None):
    select_source = selects if selects is not None else _default_selects()
    monkeypatch.setattr(cfg.questionary, "text", lambda *a, **k: _stub(next(texts)))
    monkeypatch.setattr(cfg.questionary, "confirm", lambda *a, **k: _stub(next(confirms)))
    monkeypatch.setattr(cfg.questionary, "checkbox", lambda *a, **k: _stub(next(checkboxes)))
    monkeypatch.setattr(cfg.questionary, "select", lambda *a, **k: _stub(next(select_source)))
    monkeypatch.setattr(
        cfg, "_wizard_menu_select", lambda profile_data=None: _stub(next(select_source))
    )


def test_wizard_writes_remote_only_and_parses_salary(monkeypatch, tmp_path):
    texts = iter(["Alice", "Writer, Editor", "NYC", "resume.pdf", "65,000", ""])
    confirms = iter([True, True, False, False, False])
    checkboxes = iter([["ats:greenhouse", "ats:ashby"], ["pdf", "csv"]])
    _install_wizard_stubs(monkeypatch, texts, confirms, checkboxes)
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard()
    data = load_config(path)

    assert data["search"]["remote_only"] is True
    assert data["search"]["include_hybrid"] is True
    assert data["search"]["min_salary"] == 65000
    assert data["debug"] is False


def test_wizard_saves_the_boards_picked_from_the_catalog(monkeypatch, tmp_path):
    texts = iter(["Alice", "Writer, Editor", "NYC", "resume.pdf", "", ""])
    confirms = iter([True, True, False, False, False])
    checkboxes = iter(
        [["jobspy:indeed", "jobspy:glassdoor", "ats:lever"], ["pdf", "csv"]]
    )
    _install_wizard_stubs(monkeypatch, texts, confirms, checkboxes)
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard()
    data = load_config(path)

    assert data["sources"]["jobspy"]["sites"] == ["indeed", "glassdoor"]
    assert data["sources"]["lever"]["enabled"] is True
    assert data["sources"]["greenhouse"]["enabled"] is False
    assert data["sources"]["enabled"] == ["jobspy", "ats"]
    assert data["platforms"]["lever"] is True
    assert data["platforms"]["greenhouse"] is False


def test_wizard_reparses_invalid_salary(monkeypatch, tmp_path):
    texts = iter(["Alice", "Writer", "NYC", "resume.pdf", "abc", "65k", ""])
    confirms = iter([False, True, False, False, False])
    checkboxes = iter([["ats:greenhouse"], ["pdf"]])
    _install_wizard_stubs(monkeypatch, texts, confirms, checkboxes)
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard()
    data = load_config(path)

    assert data["search"]["min_salary"] == 65000


def test_wizard_enables_debug_logging(monkeypatch, tmp_path):
    texts = iter(["Alice", "Writer", "NYC", "resume.pdf", "", ""])
    confirms = iter([False, True, False, False, True])
    checkboxes = iter([["ats:greenhouse"], ["pdf"]])
    _install_wizard_stubs(monkeypatch, texts, confirms, checkboxes)
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard()
    data = load_config(path)

    assert data["debug"] is True


def test_wizard_can_edit_an_answer_before_submitting(monkeypatch, tmp_path):
    texts = iter(["Alice", "Writer", "NYC", "resume.pdf", "", "", "Editor"])
    confirms = iter([False, True, False, False, False])
    checkboxes = iter([["ats:greenhouse"], ["pdf"]])
    selects = iter(
        ["Create a new profile", "Edit an answer", "Job titles", "Submit profile", "Exit"]
    )
    _install_wizard_stubs(monkeypatch, texts, confirms, checkboxes, selects)
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard()
    data = load_config(path)

    assert data["search"]["titles"] == ["Editor"]


def test_wizard_validates_track_color(monkeypatch, tmp_path):
    texts = iter(["Alice", "Writer", "NYC", "resume.pdf", "", "", "Tech Writer", "badcolor", "navy", "track.pdf", "api", ""])
    confirms = iter([False, True, False, True, False])
    checkboxes = iter([["ats:greenhouse"], ["pdf"]])
    _install_wizard_stubs(monkeypatch, texts, confirms, checkboxes)
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard()
    data = load_config(path)

    assert data["resume"]["tracks"][0]["color"] == "navy"
    assert data["resume"]["tracks"][0]["path"] == "track.pdf"


def test_wizard_show_recent_logs_choice(monkeypatch, tmp_path, capsys):
    texts = iter(["Alice", "Writer", "NYC", "resume.pdf", "", ""])
    confirms = iter([False, True, False, False, False])
    checkboxes = iter([["ats:greenhouse"], ["pdf"]])
    selects = iter(["Create a new profile", "Show recent logs", "Submit profile", "Exit"])
    _install_wizard_stubs(monkeypatch, texts, confirms, checkboxes, selects)
    monkeypatch.setattr(
        cfg, "recent_log_lines", lambda log_dir=None, lines=50: ["2026-01-01 sweep: scraping\n"]
    )
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard()
    data = load_config(path)

    assert "2026-01-01 sweep: scraping" in capsys.readouterr().out
    assert data["name"] == "Alice"


def test_wizard_show_recent_logs_empty(monkeypatch, tmp_path):
    texts = iter(["Alice", "Writer", "NYC", "resume.pdf", "", ""])
    confirms = iter([False, True, False, False, False])
    checkboxes = iter([["ats:greenhouse"], ["pdf"]])
    selects = iter(["Create a new profile", "Show recent logs", "Submit profile", "Exit"])
    _install_wizard_stubs(monkeypatch, texts, confirms, checkboxes, selects)
    monkeypatch.setattr(cfg, "recent_log_lines", lambda log_dir=None, lines=50: [])
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard()
    data = load_config(path)

    assert data["name"] == "Alice"


def test_wizard_converts_docx_resume_to_pdf(monkeypatch, tmp_path):
    texts = iter(["Alice", "Writer", "NYC", "resume.docx", "", "65,000", ""])
    confirms = iter([True, True, True, False, False, False])
    checkboxes = iter([["ats:greenhouse", "ats:ashby"], ["pdf", "csv"]])
    _install_wizard_stubs(monkeypatch, texts, confirms, checkboxes)
    monkeypatch.setattr(cfg, "convert_to_pdf", lambda source, out=None: "out.pdf")
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard()
    data = load_config(path)

    assert data["resume"]["path"] == "out.pdf"


def test_parse_int_and_parse_float():
    assert cfg._parse_int("24") == 24
    assert cfg._parse_int("1,024") == 1024
    assert cfg._parse_int("0") == 0
    assert cfg._parse_int("") is None
    assert cfg._parse_int("abc") is None
    assert cfg._parse_float("1.5") == 1.5
    assert cfg._parse_float("2") == 2.0
    assert cfg._parse_float("") is None
    assert cfg._parse_float("abc") is None
    assert cfg._parse_float("inf") is None
    assert cfg._parse_float("-inf") is None
    assert cfg._parse_float("nan") is None


def test_empty_platform_selection_stays_empty(monkeypatch):
    monkeypatch.setattr(cfg.questionary, "checkbox", lambda *a, **k: _stub([]))

    assert cfg._ask_platforms(current={}) == {}


def test_format_selection_requires_at_least_one_format(monkeypatch, caplog):
    answers = iter([[], ["json"]])
    monkeypatch.setattr(
        cfg.questionary,
        "checkbox",
        lambda *a, **k: _stub(next(answers)),
    )

    with caplog.at_level(logging.WARNING, logger="sweepy.engine.config"):
        assert cfg._ask_formats() == ["json"]

    assert "Select at least one export format." in caplog.text


def test_list_profiles_returns_sorted_yaml_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cfg._list_profiles() == []

    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "b_profile.yaml").write_text("name: B\n", encoding="utf-8")
    (profiles / "a_profile.yml").write_text("name: A\n", encoding="utf-8")
    (profiles / "notes.txt").write_text("ignore me\n", encoding="utf-8")

    assert cfg._list_profiles() == ["profiles/a_profile.yml", "profiles/b_profile.yaml"]


def test_last_profile_tracks_saved_profile(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert cfg.last_profile_path() is None

    path = cfg.save_profile(
        {"name": "Alice", "search": {"titles": ["Writer"]}}, "profiles/alice_writer.yaml"
    )

    assert path == "profiles/alice_writer.yaml"
    assert cfg.last_profile_path() == os.path.abspath(path)


def test_last_profile_falls_back_to_newest_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    older = profiles / "older.yaml"
    newer = profiles / "newer.yaml"
    older.write_text("name: Older\n", encoding="utf-8")
    newer.write_text("name: Newer\n", encoding="utf-8")
    os.utime(older, (1_000_000, 1_000_000))
    os.utime(newer, (2_000_000, 2_000_000))

    assert cfg.last_profile_path() == "profiles/newer.yaml"


def test_last_profile_ignores_stale_pointer(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "profiles").mkdir()
    (tmp_path / "profiles" / "keeper.yaml").write_text("name: K\n", encoding="utf-8")
    cfg.record_last_profile("profiles/deleted.yaml")

    assert cfg.last_profile_path() == "profiles/keeper.yaml"


def test_main_menu_renders_profile_tiles_and_supports_horizontal_navigation(monkeypatch):
    monkeypatch.setattr(
        cfg.shutil, "get_terminal_size", lambda fallback: SimpleNamespace(columns=80, lines=24)
    )
    monkeypatch.delenv("NO_COLOR", raising=False)

    with create_pipe_input() as pipe_input:
        question = cfg._wizard_menu_select(
            {
                "name": "Alex Rivera",
                "search": {"titles": ["Technical Writer", "Documentation Engineer"]},
                "resume": {"path": "resume.pdf"},
            },
            input=pipe_input,
            output=DummyOutput(),
        )
        pipe_input.send_bytes(b"\x1b[C\r")

        assert cfg._ask(question) == cfg.MENU_CREATE

    rendered = question.application.layout.container.content.text()
    assert "BUILD PROFILE" in "".join(fragment[1] for fragment in rendered)
    assert "Current profile: Alex Rivera  /  2 titles  /  Ready" in "".join(
        fragment[1] for fragment in rendered
    )


def test_odd_tile_count_centers_the_last_tile(monkeypatch):
    monkeypatch.setattr(
        cfg.shutil, "get_terminal_size", lambda fallback: SimpleNamespace(columns=80, lines=24)
    )
    monkeypatch.setattr(cfg, "_MENU_TILES", cfg._MENU_TILES[:5])

    with create_pipe_input() as pipe_input:
        question = cfg._wizard_menu_select(input=pipe_input, output=DummyOutput())

    rendered = "".join(
        fragment[1] for fragment in question.application.layout.container.content.text()
    )
    card_rows = [
        line
        for line in rendered.splitlines()
        if "╭" in line and "│" in line and "┤" not in line
    ]
    assert card_rows[-1].index("╭") > card_rows[0].index("╭")


def test_toolbox_keeps_secondary_actions_available():
    assert cfg._toolbox_choices() == [
        cfg.MENU_EDIT,
        cfg.MENU_SOURCES,
        cfg.MENU_ENGINES,
        cfg.MENU_AGGREGATORS,
        cfg.MENU_DEBUG,
        cfg.MENU_HELP,
        cfg.MENU_LOGS,
        cfg.MENU_CONVERT,
        cfg.MENU_UPDATE,
        cfg.MENU_EXIT,
    ]


def test_welcome_banner_uses_a_centered_color_ready_panel(capsys):
    cfg._print_welcome_banner()

    output = capsys.readouterr().out
    assert "S W E E P Y" in output
    assert "Search smarter, better, faster, stronger." in output
    assert "Modern job searching requires modern solutions." in output
    assert "╔" in output
    assert "\x1b[" not in output
    banner_lines = output.splitlines()
    slogan_line = next(line for line in banner_lines if "KNICKS IN FIVE" in line)
    bottom_border_index = next(
        index for index, line in enumerate(banner_lines) if line.startswith("╚")
    )
    assert banner_lines.index(slogan_line) == bottom_border_index + 1
    assert not slogan_line.startswith("║")
    assert len(slogan_line[: slogan_line.index("KNICKS IN FIVE")]) == len(
        slogan_line[slogan_line.index("KNICKS IN FIVE") + len("KNICKS IN FIVE") :]
    )


def test_button_choices_keep_values_and_square_brackets():
    choices = cfg._button_choices(["Run a sweep", "Exit"])

    assert [choice.value for choice in choices] == ["Run a sweep", "Exit"]
    assert choices[0].title.startswith("[ ")
    assert choices[0].title.endswith(" ]")
    assert len(choices[0].title) == len(choices[1].title)


def test_select_returns_the_original_button_value():
    with create_pipe_input() as pipe_input:
        question = cfg._select(
            "Action",
            ["First action", "Second action"],
            input=pipe_input,
            output=DummyOutput(),
        )
        pipe_input.send_bytes(b"\x1b[B\r")
        assert cfg._ask(question) == "Second action"


def test_select_styles_buttons_and_preserves_default(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    captured = {}

    def select(message, choices, style, **kwargs):
        captured.update(message=message, choices=choices, style=style, **kwargs)
        return _stub("legacy")

    monkeypatch.setattr(cfg.questionary, "select", select)

    question = cfg._select("Report style:", ["cards", "legacy"], default="legacy")

    assert question.unsafe_ask() == "legacy"
    assert captured["message"] == "Report style:"
    assert [choice.value for choice in captured["choices"]] == ["cards", "legacy"]
    assert captured["style"] is cfg._MENU_STYLE
    assert captured["default"] == "legacy"


def test_select_honors_no_color_environment(monkeypatch):
    captured = {}
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr(
        cfg.questionary,
        "select",
        lambda message, choices, style, **kwargs: captured.update(style=style),
    )

    cfg._select("Action", ["First"])

    assert captured["style"] is cfg._NO_COLOR_STYLE


def test_menu_choices_show_primary_tiles_and_toolbox_contains_utilities():
    choices = [tile[3] for tile in cfg._MENU_TILES]
    assert choices == [
        cfg.MENU_RUN,
        cfg.MENU_CREATE,
        cfg.MENU_LOAD,
        cfg.MENU_SCALING,
        cfg.MENU_TOOLBOX,
        cfg.MENU_EXIT,
    ]
    assert cfg.MENU_UPDATE in cfg._toolbox_choices()
    assert cfg.MENU_EXIT in cfg._toolbox_choices()


def test_menu_tiles_fill_a_balanced_grid():
    assert len(cfg._MENU_TILES) % 2 == 0


def test_menu_tile_text_fits_the_narrowest_two_column_card():
    # Below 70 columns the launchpad switches to one column, so 70 is the tightest grid.
    inner_width = (70 - 2 - 9) // 2 - 2
    for number, title, description, _ in cfg._MENU_TILES:
        assert len(f" {number}  {title}") < inner_width
        assert len(f" {description}") < inner_width


def test_exit_tile_closes_the_wizard(monkeypatch):
    monkeypatch.setattr(cfg, "_print_welcome_banner", lambda: None)
    tiles = [tile[3] for tile in cfg._MENU_TILES]
    assert tiles[-1] == cfg.MENU_EXIT

    monkeypatch.setattr(
        cfg, "_wizard_menu_select", lambda profile_data=None: _stub(cfg.MENU_EXIT)
    )
    assert cfg.run_wizard() is None


def test_menu_choices_start_with_run_entry():
    choices = [tile[3] for tile in cfg._MENU_TILES]
    assert choices[0] == cfg.MENU_RUN == "Run a sweep"


def test_wizard_run_entry_sweeps_with_the_loaded_profile(monkeypatch, tmp_path):
    profile = {"name": "Alex", "search": {"titles": ["Paralegal"]}}
    monkeypatch.setattr(
        cfg, "_load_profile_flow", lambda path=None: ("profiles/alex.yaml", profile)
    )

    calls = []
    _install_wizard_stubs(
        monkeypatch, iter([]), iter([]), iter([]), iter([cfg.MENU_RUN, "Exit"])
    )
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard(
        "profiles/alex.yaml", run_sweep=lambda data, where: calls.append((data, where))
    )

    assert path == "profiles/alex.yaml"
    assert calls == [(profile, "profiles/alex.yaml")]


def test_wizard_loads_existing_profile_from_main_menu(monkeypatch, tmp_path):
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "alex.yaml").write_text(
        "name: Alex\nsearch:\n  titles:\n    - Paralegal\n", encoding="utf-8"
    )
    calls = []
    selects = iter(
        [
            cfg.MENU_LOAD,
            "profiles/alex.yaml",
            cfg.MENU_RUN,
            "Exit",
        ]
    )
    _install_wizard_stubs(monkeypatch, iter([]), iter([]), iter([]), selects)
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard(
        run_sweep=lambda data, where: calls.append((data, where))
    )

    assert path == "profiles/alex.yaml"
    assert calls == [
        ({"name": "Alex", "search": {"titles": ["Paralegal"]}}, "profiles/alex.yaml")
    ]
    assert cfg.last_profile_path() == os.path.abspath(path)


def test_wizard_run_entry_requires_a_profile(monkeypatch, tmp_path, caplog):
    calls = []
    _install_wizard_stubs(
        monkeypatch, iter([]), iter([]), iter([]), iter([cfg.MENU_RUN, "Exit"])
    )
    monkeypatch.chdir(tmp_path)

    with caplog.at_level(logging.WARNING, logger="sweepy.engine.config"):
        assert cfg.run_wizard(run_sweep=lambda *args: calls.append(args)) is None

    assert calls == []
    assert any(
        "Create or edit a profile first" in record.getMessage() for record in caplog.records
    )


def test_wizard_update_entry_runs_updater(monkeypatch, tmp_path, capsys):
    _install_wizard_stubs(
        monkeypatch, iter([]), iter([]), iter([]), iter(["Update Sweepy", "Exit"])
    )
    monkeypatch.setattr(
        cfg, "update_sweepy", lambda: "Sweepy is already up to date (v2.4.0)."
    )
    monkeypatch.chdir(tmp_path)

    assert cfg.run_wizard() is None
    assert "already up to date" in capsys.readouterr().out


def test_wizard_show_help_lists_flags_and_links(monkeypatch, tmp_path, capsys):
    _install_wizard_stubs(
        monkeypatch,
        iter([]),
        iter([]),
        iter([]),
        iter(["Show help", cfg.BACK_LABEL, "Exit"]),
    )
    monkeypatch.chdir(tmp_path)

    assert cfg.run_wizard() is None

    out = capsys.readouterr().out
    assert "python swee.py --run" in out
    assert cfg.DOCS_URL in out
    assert cfg.README_URL in out


def test_wizard_converts_any_document_without_a_profile(monkeypatch, tmp_path, capsys):
    source = tmp_path / "notes.md"
    source.write_text("# Alex\n\n- Westlaw\n", encoding="utf-8")
    _install_wizard_stubs(
        monkeypatch,
        iter([str(source), ""]),
        iter([]),
        iter([]),
        iter([cfg.MENU_CONVERT, "Exit"]),
    )
    monkeypatch.chdir(tmp_path)

    assert cfg.run_wizard() is None

    assert (tmp_path / "notes.pdf").exists()
    assert "PDF saved:" in capsys.readouterr().out


def test_wizard_conversion_retries_after_a_bad_path(monkeypatch, tmp_path, caplog):
    good = tmp_path / "notes.txt"
    good.write_text("Alex Rivera\n", encoding="utf-8")
    _install_wizard_stubs(
        monkeypatch,
        iter(["nope.txt", "", str(good), ""]),
        iter([]),
        iter([]),
        iter([cfg.MENU_CONVERT, "Exit"]),
    )
    monkeypatch.chdir(tmp_path)

    with caplog.at_level(logging.WARNING, logger="sweepy.engine.config"):
        assert cfg.run_wizard() is None

    assert (tmp_path / "notes.pdf").exists()
    assert any(
        "Could not convert the file" in record.getMessage() for record in caplog.records
    )


def _rich_profile():
    return {
        "name": "Alex",
        "debug": True,
        "search": {
            "titles": ["Paralegal"],
            "location": "NYC",
            "remote_only": True,
            "include_hybrid": False,
            "min_salary": 65000,
        },
        "resume": {
            "path": "resume.pdf",
            "must_have_skills": ["Westlaw"],
            "keywords_weight": 2.0,
            "synonyms": [["docs-as-code", "documentation as code"]],
            "tracks": [
                {
                    "name": "Track",
                    "path": "track.pdf",
                    "color": "navy",
                    "route_keywords": ["api"],
                }
            ],
        },
        "platforms": {
            "greenhouse": True,
            "ashby": False,
            "lever": False,
            "workable": False,
            "aggregators": True,
            "custom": [{"name": "Breezy HR", "domain": "breezy.hr", "enabled": True}],
        },
        "sources": {"jobspy": {"linkedin": False}},
        "report": {
            "style": "legacy",
            "cards_per_page": 2,
            "max_cards": 5,
            "destinations": ["D:/reports"],
        },
        "export": {"format": "pdf,json", "output_dir": "out"},
    }


def test_answers_round_trip_preserves_untouched_sections():
    profile = _rich_profile()

    answers = cfg._answers_from_profile(profile)
    merged = cfg._merge_answers(profile, answers)

    assert merged == profile
    assert merged["sources"] == {"jobspy": {"linkedin": False}}
    assert merged["resume"]["synonyms"] == profile["resume"]["synonyms"]
    assert merged["report"]["destinations"] == ["D:/reports"]


def test_merge_answers_drops_tracks_and_custom_when_cleared():
    profile = _rich_profile()
    answers = cfg._answers_from_profile(profile)
    answers["tracks"] = []
    answers["custom_platforms"] = []

    merged = cfg._merge_answers(profile, answers)

    assert "tracks" not in merged["resume"]
    assert "custom" not in merged["platforms"]
    assert merged["resume"]["synonyms"] == profile["resume"]["synonyms"]


def test_wizard_toggles_debug_and_saves_on_exit(monkeypatch, tmp_path):
    texts = iter(["Alice", "Writer", "NYC", "resume.pdf", "", ""])
    confirms = iter([False, True, False, False, False, True])
    checkboxes = iter([["ats:greenhouse"], ["pdf"]])
    selects = iter(
        [
            "Create a new profile",
            "Submit profile",
            "Toggle debug logging",
            "Exit",
            "Overwrite profiles/alice_writer.yaml",
        ]
    )
    _install_wizard_stubs(monkeypatch, texts, confirms, checkboxes, selects)
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard()
    data = load_config(path)

    assert data["debug"] is True


def test_wizard_scaling_editor_validates_and_saves(monkeypatch, tmp_path):
    texts = iter(
        [
            "Alice",
            "Writer",
            "NYC",
            "resume.pdf",
            "",
            "",
            "abc",
            "2.0",
            "-1",
            "10",
            "0",
            "3",
        ]
    )
    confirms = iter([False, True, False, False, False, True])
    checkboxes = iter([["ats:greenhouse"], ["pdf"]])
    selects = iter(
        [
            "Create a new profile",
            "Submit profile",
            "Adjust scoring and scaling",
            "Keyword weight (resume.keywords_weight)",
            "Maximum cards (report.max_cards)",
            "Cards per page (report.cards_per_page)",
            "Report style (report.style)",
            "legacy",
            cfg.BACK_LABEL,
            "Exit",
            "Overwrite profiles/alice_writer.yaml",
        ]
    )
    _install_wizard_stubs(monkeypatch, texts, confirms, checkboxes, selects)
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard()
    data = load_config(path)

    assert data["resume"]["keywords_weight"] == 2.0
    assert data["report"]["max_cards"] == 10
    assert data["report"]["cards_per_page"] == 3
    assert data["report"]["style"] == "legacy"


def test_scaling_editor_toggles_history_and_retention(monkeypatch):
    menus = iter(
        [
            "Skip previously reported postings (history)",
            "History retention in days (history.retention_days)",
            None,
        ]
    )
    replies = iter([False, "14"])
    monkeypatch.setattr(cfg, "_menu", lambda *a, **k: next(menus))
    monkeypatch.setattr(cfg, "_ask", lambda question: next(replies))
    monkeypatch.setattr(cfg.questionary, "confirm", lambda *a, **k: object())
    monkeypatch.setattr(cfg.questionary, "text", lambda *a, **k: object())

    profile = {"resume": {}, "report": {}}
    changed = cfg._edit_scaling(profile)

    assert changed is True
    assert profile["history"] == {"enabled": False, "retention_days": 14}


def test_wizard_aggregator_editor_adds_custom_aggregator(monkeypatch, tmp_path):
    texts = iter(
        [
            "Alice",
            "Writer",
            "NYC",
            "resume.pdf",
            "",
            "",
            "SmartRecruiters",
            "SmartRecruiters.com",
        ]
    )
    confirms = iter([False, True, False, False, False, True])
    checkboxes = iter([["ats:greenhouse"], ["pdf"]])
    selects = iter(
        [
            "Create a new profile",
            "Submit profile",
            "Add or edit aggregators",
            "Toggle aggregator feeds",
            "Add a custom aggregator",
            cfg.BACK_LABEL,
            "Exit",
            "Overwrite profiles/alice_writer.yaml",
        ]
    )
    _install_wizard_stubs(monkeypatch, texts, confirms, checkboxes, selects)
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard()
    data = load_config(path)

    assert data["platforms"]["aggregators"] is True
    assert data["platforms"]["custom"] == [
        {"name": "SmartRecruiters", "domain": "smartrecruiters.com", "enabled": True}
    ]


def test_wizard_aggregator_editor_removes_custom_aggregator(monkeypatch, tmp_path):
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "has_custom.yaml").write_text(
        "name: Alex\n"
        "search:\n"
        "  titles:\n"
        "    - Paralegal\n"
        "platforms:\n"
        "  greenhouse: true\n"
        "  custom:\n"
        "    - name: Breezy HR\n"
        "      domain: breezy.hr\n"
        "      enabled: true\n",
        encoding="utf-8",
    )
    selects = iter(
        [
            "Edit an existing profile",
            "profiles/has_custom.yaml",
            "Submit changes",
            "Overwrite profiles/has_custom.yaml",
            "Add or edit aggregators",
            "Remove a custom aggregator",
            "Breezy HR (breezy.hr)",
            cfg.BACK_LABEL,
            "Exit",
            "Overwrite profiles/has_custom.yaml",
        ]
    )
    _install_wizard_stubs(
        monkeypatch, iter([]), iter([True]), iter([[]]), selects
    )
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard()
    data = load_config(path)

    assert "custom" not in data["platforms"]


def test_wizard_edits_existing_profile_in_place(monkeypatch, tmp_path):
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "legacy.yaml").write_text(
        "name: Alex\n"
        "search:\n"
        "  titles:\n"
        "    - Paralegal\n"
        "resume:\n"
        "  synonyms:\n"
        "    - [docs-as-code, documentation as code]\n"
        "sources:\n"
        "  jobspy:\n"
        "    linkedin: false\n",
        encoding="utf-8",
    )
    selects = iter(
        [
            "Edit an existing profile",
            "profiles/legacy.yaml",
            "Edit an answer",
            "Job titles",
            "Submit changes",
            "Overwrite profiles/legacy.yaml",
            "Exit",
        ]
    )
    _install_wizard_stubs(monkeypatch, iter(["Editor"]), iter([]), iter([]), selects)
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard()
    data = load_config(path)

    assert path == "profiles/legacy.yaml"
    assert data["search"]["titles"] == ["Editor"]
    assert data["resume"]["synonyms"] == [["docs-as-code", "documentation as code"]]
    assert data["sources"] == {"jobspy": {"linkedin": False}}


def test_wizard_edits_existing_profile_as_new_file(monkeypatch, tmp_path):
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    original = "name: Alex\nsearch:\n  titles:\n    - Paralegal\n"
    (profiles / "legacy.yaml").write_text(original, encoding="utf-8")
    selects = iter(
        [
            "Edit an existing profile",
            "profiles/legacy.yaml",
            "Submit changes",
            "Save as a new file",
            "Exit",
        ]
    )
    _install_wizard_stubs(
        monkeypatch, iter(["profiles/copied.yaml"]), iter([]), iter([]), selects
    )
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard()

    assert path == "profiles/copied.yaml"
    assert (profiles / "legacy.yaml").read_text(encoding="utf-8") == original
    assert load_config(path)["name"] == "Alex"


def test_wizard_exits_without_a_profile(monkeypatch, tmp_path):
    _install_wizard_stubs(monkeypatch, iter([]), iter([]), iter([]), iter(["Exit"]))
    monkeypatch.chdir(tmp_path)

    assert cfg.run_wizard() is None


def test_wizard_exit_remains_available_from_toolbox(monkeypatch, tmp_path):
    _install_wizard_stubs(
        monkeypatch,
        iter([]),
        iter([]),
        iter([]),
        iter([cfg.MENU_TOOLBOX, cfg.MENU_EXIT]),
    )
    monkeypatch.chdir(tmp_path)

    assert cfg.run_wizard() is None


def test_wizard_edit_choice_warns_without_profiles(monkeypatch, tmp_path):
    selects = iter(["Edit an existing profile", "Exit"])
    _install_wizard_stubs(monkeypatch, iter([]), iter([]), iter([]), selects)
    monkeypatch.chdir(tmp_path)

    assert cfg.run_wizard() is None


def test_wizard_loads_profile_path_directly(monkeypatch, tmp_path):
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "legacy.yaml").write_text(
        "name: Alex\nsearch:\n  titles:\n    - Paralegal\n", encoding="utf-8"
    )
    selects = iter(
        [
            "Submit changes",
            "Overwrite profiles/legacy.yaml",
            "Exit",
        ]
    )
    _install_wizard_stubs(monkeypatch, iter([]), iter([]), iter([]), selects)
    monkeypatch.chdir(tmp_path)

    path = cfg.run_wizard("profiles/legacy.yaml")

    assert path == "profiles/legacy.yaml"
    assert load_config(path)["name"] == "Alex"


def test_wizard_missing_profile_path_falls_back_to_menu(monkeypatch, tmp_path):
    _install_wizard_stubs(monkeypatch, iter([]), iter([]), iter([]), iter(["Exit"]))
    monkeypatch.chdir(tmp_path)

    assert cfg.run_wizard("profiles/gone.yaml") is None


def test_resume_path_hint_matches_the_platform(monkeypatch):
    monkeypatch.setattr(cfg.sys, "platform", "win32")
    assert "Ctrl+Shift+C" in cfg._resume_path_hint()
    assert "File Explorer" in cfg._resume_path_hint()

    monkeypatch.setattr(cfg.sys, "platform", "darwin")
    assert "Option+Command+C" in cfg._resume_path_hint()
    assert "Finder" in cfg._resume_path_hint()

    monkeypatch.setattr(cfg.sys, "platform", "linux")
    hint = cfg._resume_path_hint()
    assert "file manager" in hint
    assert "Ctrl+Shift+C" in hint


def test_resume_path_prompt_shows_the_hint(monkeypatch):
    captured = {}

    def fake_text(message, **kwargs):
        captured["message"] = message
        return _stub("resume.pdf")

    monkeypatch.setattr(cfg.sys, "platform", "win32")
    monkeypatch.setattr(cfg.questionary, "text", fake_text)

    assert cfg._ask_resume_path() == "resume.pdf"
    assert "What is the path to your resume PDF?" in captured["message"]
    assert "Ctrl+Shift+C" in captured["message"]


def test_track_resume_path_prompt_shows_the_hint(monkeypatch):
    messages = []
    answers = iter(["Tech Writer", "track.pdf", "", ""])

    def fake_text(message, **kwargs):
        messages.append(message)
        return _stub(next(answers))

    monkeypatch.setattr(cfg.sys, "platform", "win32")
    monkeypatch.setattr(cfg.questionary, "text", fake_text)
    monkeypatch.setattr(cfg.questionary, "confirm", lambda *a, **k: _stub(True))
    monkeypatch.setattr(cfg, "_ask_color", lambda name: "navy")

    tracks = cfg._ask_tracks()

    track_prompt = next(m for m in messages if "track" in m)
    assert "Ctrl+Shift+C" in track_prompt
    assert tracks == [
        {"name": "Tech Writer", "color": "navy", "path": "track.pdf", "route_keywords": []}
    ]
