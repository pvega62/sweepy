import pytest

import engine.config as config


class _Answer:
    """Stand-in for a questionary prompt that already holds its answer."""

    def __init__(self, value):
        self.value = value

    def unsafe_ask(self):
        return self.value


@pytest.fixture(autouse=True)
def promptless(monkeypatch):
    for name in ("confirm", "text", "checkbox", "password", "select"):
        monkeypatch.setattr(config.questionary, name, lambda *a, **k: _Answer(None))
    monkeypatch.setattr(config, "_ask", lambda question: question.unsafe_ask())


def _menu_choices(monkeypatch, answer):
    """Capture the choices a menu renders, then answer with ``answer``."""
    captured = {}

    def fake_select(message, choices=None, **kwargs):
        captured["values"] = [choice.value for choice in choices]
        return _Answer(answer)

    monkeypatch.setattr(config.questionary, "select", fake_select)
    return captured


def test_menu_puts_back_first_and_maps_it_to_none(monkeypatch):
    captured = _menu_choices(monkeypatch, config.BACK_LABEL)
    assert config._menu("Pick one", ["Alpha", "Beta"]) is None
    assert captured["values"] == [config.BACK_LABEL, "Alpha", "Beta"]


def test_menu_escape_is_the_same_as_back(monkeypatch):
    monkeypatch.setattr(config.questionary, "select", lambda *a, **k: _Answer("Alpha"))

    def escape(_question):
        raise config._GoBack()

    monkeypatch.setattr(config, "_ask", escape)
    assert config._menu("Pick one", ["Alpha"]) is None


def test_menu_passes_actions_through(monkeypatch):
    _menu_choices(monkeypatch, "Beta")
    assert config._menu("Pick one", ["Alpha", "Beta"]) == "Beta"


@pytest.mark.parametrize(
    "run",
    [
        pytest.param(lambda: config._show_help_menu(), id="help"),
        pytest.param(lambda: config._run_toolbox(None, None, False), id="toolbox"),
        pytest.param(
            lambda: config._edit_scaling({"resume": {}, "report": {}}), id="scaling"
        ),
        pytest.param(lambda: config._edit_aggregators({"platforms": {}}), id="aggregators"),
        pytest.param(lambda: config._manage_engines(), id="engines"),
        pytest.param(lambda: config._edit_sources({"sources": {}}), id="sources"),
    ],
)
def test_every_submenu_offers_back_as_the_first_choice(monkeypatch, run):
    captured = _menu_choices(monkeypatch, config.BACK_LABEL)
    run()
    assert captured["values"][0] == config.BACK_LABEL


def test_toolbox_back_returns_to_the_launchpad(monkeypatch):
    _menu_choices(monkeypatch, config.BACK_LABEL)
    profile = {"name": "Alex"}

    result = config._run_toolbox(profile, "profiles/alex.yaml", True)

    assert result == (profile, "profiles/alex.yaml", True, False)


def test_toolbox_exit_asks_the_wizard_to_close(monkeypatch):
    _menu_choices(monkeypatch, config.MENU_EXIT)

    profile, path, dirty, exit_requested = config._run_toolbox(None, None, False)

    assert (profile, path, dirty) == (None, None, False)
    assert exit_requested is True


def test_submenu_returns_to_the_toolbox_not_the_launchpad(monkeypatch):
    calls = []
    monkeypatch.setattr(config, "_print_welcome_banner", lambda: None)
    monkeypatch.setattr(config, "_manage_engines", lambda: calls.append("engines"))

    answers = iter(
        [config.MENU_TOOLBOX, config.MENU_ENGINES, config.BACK_LABEL, config.MENU_EXIT]
    )
    monkeypatch.setattr(
        config, "_wizard_menu_select", lambda profile_data=None: _Answer(next(answers))
    )
    monkeypatch.setattr(config.questionary, "select", lambda *a, **k: _Answer(next(answers)))

    assert config.run_wizard() is None
    assert calls == ["engines"]


def test_escape_at_the_launchpad_exits(monkeypatch):
    monkeypatch.setattr(config, "_print_welcome_banner", lambda: None)

    def escape(profile_data=None):
        raise config._GoBack()

    monkeypatch.setattr(config, "_wizard_menu_select", escape)
    assert config.run_wizard() is None


def test_ctrl_c_still_cancels_the_wizard(monkeypatch):
    monkeypatch.setattr(config, "_print_welcome_banner", lambda: None)

    def cancel(profile_data=None):
        raise KeyboardInterrupt

    monkeypatch.setattr(config, "_wizard_menu_select", cancel)

    with pytest.raises(SystemExit) as error:
        config.run_wizard()
    assert error.value.code == 0


def test_collect_escape_reopens_the_previous_question():
    asked = []

    def first(current=None):
        asked.append("first")
        return "one"

    def second(current=None):
        asked.append("second")
        if asked.count("second") == 1:
            raise config._GoBack()
        return "two"

    steps = [config._Step("a", "A", first), config._Step("b", "B", second)]
    assert config._collect(steps) == {"a": "one", "b": "two"}
    assert asked == ["first", "second", "first", "second"]


def test_collect_escape_on_the_first_question_leaves_the_flow():
    def first(current=None):
        raise config._GoBack()

    with pytest.raises(config._GoBack):
        config._collect([config._Step("a", "A", first)])


def test_create_flow_backs_out_without_saving(monkeypatch):
    monkeypatch.setattr(config, "_build_steps", lambda: [])
    monkeypatch.setattr(config, "_collect", lambda steps: (_ for _ in ()).throw(config._GoBack()))
    monkeypatch.setattr(config, "save_profile", lambda *a, **k: pytest.fail("saved"))

    assert config._create_profile_flow() is None


def test_review_back_reopens_the_last_question(monkeypatch):
    reopened = []

    def last(current=None):
        reopened.append(current)
        return "revised"

    answers = {"name": "original"}
    monkeypatch.setattr(config, "_print_summary", lambda a, s: None)
    _menu_choices(monkeypatch, config.BACK_LABEL)
    monkeypatch.setattr(
        config.questionary,
        "select",
        _sequenced(config.BACK_LABEL, "Submit profile"),
    )

    config._review_answers(answers, [config._Step("name", "Name", last)], lambda: {})

    assert reopened == ["original"]
    assert answers["name"] == "revised"


def test_review_edit_escape_returns_to_the_review(monkeypatch):
    def raise_back(current=None):
        raise config._GoBack()

    answers = {"name": "original"}
    monkeypatch.setattr(config, "_print_summary", lambda a, s: None)
    monkeypatch.setattr(
        config.questionary,
        "select",
        _sequenced("Edit an answer", "Name", "Submit profile"),
    )

    config._review_answers(answers, [config._Step("name", "Name", raise_back)], lambda: {})

    assert answers["name"] == "original"


def _sequenced(*values):
    pending = list(values)

    def fake_select(message, choices=None, **kwargs):
        return _Answer(pending.pop(0))

    return fake_select


def test_engine_picker_back_keeps_the_previous_config(monkeypatch):
    def escape(_question):
        raise config._GoBack()

    monkeypatch.setattr(config, "_ask", escape)
    assert config._ask_engines({"enabled": ["jobspy"]}) is None


def test_orchestrator_back_keeps_the_previous_settings(monkeypatch):
    def escape(_question):
        raise config._GoBack()

    monkeypatch.setattr(config, "_ask", escape)
    assert config._ask_orchestrator({"timeout_per_source_seconds": 90}) is None


def test_edit_with_back_keeps_accepted_values():
    profile = {"search": {}}

    def editor(data):
        data["search"]["titles"] = ["Writer"]
        raise config._GoBack()

    assert config._edit_with_back(editor, profile) is True
    assert profile["search"]["titles"] == ["Writer"]


def test_edit_with_back_reports_no_change():
    profile = {"search": {"titles": ["Writer"]}}

    def editor(data):
        raise config._GoBack()

    assert config._edit_with_back(editor, profile) is False


def _real_select(monkeypatch, pipe_input):
    """Route every questionary select through the pipe input that drives the test."""
    from prompt_toolkit.output import DummyOutput

    original = config.questionary.select

    def select(message, choices=None, **kwargs):
        return original(
            message, choices=choices, input=pipe_input, output=DummyOutput(), **kwargs
        )

    monkeypatch.setattr(config.questionary, "select", select)


def _real_menu(monkeypatch, pipe_input):
    """Drive the launchpad with the same pipe input as the rest of the test."""
    from prompt_toolkit.output import DummyOutput

    original = config._wizard_menu_select

    def menu(profile_data=None):
        return original(profile_data, input=pipe_input, output=DummyOutput())

    monkeypatch.setattr(config, "_wizard_menu_select", menu)
    return menu


def _stub_menu(answer):
    return type(
        "Stub",
        (),
        {"unsafe_ask": lambda self: answer},
    )()


def test_real_keys_open_the_toolbox_and_back(monkeypatch):
    """Arrow keys reach the toolbox tile, and Enter on Back redraws the launchpad."""
    import os

    from prompt_toolkit.input import create_pipe_input

    monkeypatch.setattr(config, "_print_welcome_banner", lambda: None)
    monkeypatch.setattr(
        config.shutil, "get_terminal_size", lambda *a, **k: os.terminal_size((80, 24))
    )
    calls = {"menu": 0}

    with create_pipe_input() as pipe_input:
        _real_select(monkeypatch, pipe_input)
        launchpad = _real_menu(monkeypatch, pipe_input)

        def menu(profile_data=None):
            calls["menu"] += 1
            if calls["menu"] == 1:
                return launchpad(profile_data)
            return _stub_menu(config.MENU_EXIT)

        monkeypatch.setattr(config, "_wizard_menu_select", menu)
        # Two downs reach the fifth tile (Sweepy's Toolbox) in a two-column grid.
        # Enter opens it, then Enter accepts the first entry, which is Back.
        pipe_input.send_bytes(b"\x1b[B\x1b[B\r" + b"\r")
        assert config.run_wizard() is None

    assert calls["menu"] == 2
