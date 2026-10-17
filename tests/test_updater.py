import subprocess

import engine.updater as updater


def _git(cwd, *args):
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )


def _commit(cwd, message):
    _git(cwd, "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "commit", "-m", message, "--allow-empty")


def _write(path, text):
    path.write_text(text, encoding="utf-8")


def _setup_repos(tmp_path):
    """Build a bare remote and two clones, all sharing one pushed commit."""
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    upstream = tmp_path / "upstream"

    _git(tmp_path, "init", "--bare", "--initial-branch=main", str(remote))
    _git(tmp_path, "clone", str(remote), str(work))
    _write(work / "VERSION", "2.4.0\n")
    _write(work / "requirements.txt", "# placeholder\n")
    _git(work, "add", "VERSION", "requirements.txt")
    _commit(work, "initial")
    _git(work, "push", "-u", "origin", "main")

    _git(tmp_path, "clone", str(remote), str(upstream))
    return {"remote": remote, "work": work, "upstream": upstream}


def _push_new_upstream_commit(repos, version="2.5.0"):
    _write(repos["upstream"] / "VERSION", f"{version}\n")
    _git(repos["upstream"], "add", "VERSION")
    _commit(repos["upstream"], "bump version")
    _git(repos["upstream"], "push")


def _ok():
    return updater._GitResult(0)


def test_gather_status_not_a_repo(tmp_path):
    status = updater.gather_status(str(tmp_path))
    assert status["is_repo"] is False


def test_gather_status_repo_fields(tmp_path):
    repos = _setup_repos(tmp_path)
    status = updater.gather_status(str(repos["work"]))
    assert status["is_repo"] is True
    assert status["branch"] == "main"
    assert status["remote"]
    assert status["dirty"] is False


def test_update_sweepy_not_a_repo(tmp_path):
    message = updater.update_sweepy(repo_root=str(tmp_path))
    assert "not installed from a Git repository" in message


def test_update_sweepy_no_remote(tmp_path):
    repo = tmp_path / "lonely"
    repo.mkdir()
    _git(repo, "init")
    _write(repo / "VERSION", "2.4.0\n")
    _git(repo, "add", "VERSION")
    _commit(repo, "initial")

    message = updater.update_sweepy(repo_root=str(repo))
    assert "No Git remote named 'origin'" in message


def test_update_sweepy_already_up_to_date(tmp_path):
    repos = _setup_repos(tmp_path)
    message = updater.update_sweepy(repo_root=str(repos["work"]))
    assert message == "Sweepy is already up to date (v2.4.0)."


def test_update_sweepy_pulls_and_reinstalls(tmp_path, monkeypatch):
    repos = _setup_repos(tmp_path)
    _push_new_upstream_commit(repos, version="2.5.0")

    calls = []
    monkeypatch.setattr(
        updater,
        "_reinstall_dependencies",
        lambda repo_root: calls.append(repo_root) or _ok(),
    )

    message = updater.update_sweepy(repo_root=str(repos["work"]))

    assert message == "Sweepy updated from v2.4.0 to v2.5.0."
    assert (repos["work"] / "VERSION").read_text(encoding="utf-8").strip() == "2.5.0"
    assert calls == [str(repos["work"])]


def test_update_sweepy_refuses_dirty_tree(tmp_path):
    repos = _setup_repos(tmp_path)
    _push_new_upstream_commit(repos)

    _write(repos["work"] / "VERSION", "local edit\n")

    message = updater.update_sweepy(repo_root=str(repos["work"]))

    assert "has local changes" in message
    assert (repos["work"] / "VERSION").read_text(encoding="utf-8") == "local edit\n"


def test_update_sweepy_refuses_diverged_branch(tmp_path):
    repos = _setup_repos(tmp_path)
    _push_new_upstream_commit(repos)

    _write(repos["work"] / "VERSION", "local fork\n")
    _git(repos["work"], "add", "VERSION")
    _commit(repos["work"], "local commit")

    message = updater.update_sweepy(repo_root=str(repos["work"]))

    assert "ahead of" in message
    assert "local fork" in (repos["work"] / "VERSION").read_text(encoding="utf-8")


def test_update_sweepy_reports_failed_dependency_install(tmp_path, monkeypatch):
    repos = _setup_repos(tmp_path)
    _push_new_upstream_commit(repos)

    monkeypatch.setattr(
        updater,
        "_reinstall_dependencies",
        lambda repo_root: updater._GitResult(1, stderr="no wheels"),
    )

    message = updater.update_sweepy(repo_root=str(repos["work"]))

    assert "dependency install failed" in message
    assert "no wheels" in message
    # The code itself still updated.
    assert (repos["work"] / "VERSION").read_text(encoding="utf-8").strip() == "2.5.0"


def test_check_for_updates_reports_available(tmp_path):
    repos = _setup_repos(tmp_path)
    _push_new_upstream_commit(repos)

    message = updater.check_for_updates(repo_root=str(repos["work"]))

    assert "Update available: 1 new commit(s)" in message


def test_check_for_updates_reports_up_to_date(tmp_path):
    repos = _setup_repos(tmp_path)

    message = updater.check_for_updates(repo_root=str(repos["work"]))

    assert message == "Sweepy is up to date (v2.4.0)."
