from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import List, Optional

log = logging.getLogger("sweepy.engine.updater")
_DEFAULT_REMOTE = "origin"


class _GitResult:
    """Minimal stand-in for a completed git process."""

    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _repo_root() -> str:
    """Return the repository root that contains this module."""
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def _run_git(args: List[str], repo_root: str) -> _GitResult:
    try:
        completed = subprocess.run(
            ["git", "-C", repo_root, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return _GitResult(returncode=127, stderr="git was not found on PATH.")
    return _GitResult(completed.returncode, completed.stdout, completed.stderr)


def _read_version(repo_root: str) -> str:
    version_file = os.path.join(repo_root, "VERSION")
    try:
        with open(version_file, encoding="utf-8") as f:
            return f.read().strip() or "unknown"
    except FileNotFoundError:
        return "unknown"


def current_version() -> str:
    """Return the installed Sweepy version from the repository's VERSION file."""
    return _read_version(_repo_root())


def gather_status(repo_root: str) -> dict:
    """Describe the local checkout without touching the network."""
    status = {
        "is_repo": False,
        "remote": None,
        "branch": None,
        "current": None,
        "upstream": None,
        "behind": 0,
        "ahead": 0,
        "dirty": False,
    }

    result = _run_git(["rev-parse", "--is-inside-work-tree"], repo_root)
    if result.returncode != 0:
        return status
    status["is_repo"] = True

    result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    status["branch"] = result.stdout.strip() if result.returncode == 0 else None

    result = _run_git(["rev-parse", "HEAD"], repo_root)
    status["current"] = result.stdout.strip() if result.returncode == 0 else None

    # Only tracked changes block a fast-forward pull. Untracked files such as
    # a user's own profiles/ and results/ entries stay out of the way.
    result = _run_git(["status", "--porcelain", "--untracked-files=no"], repo_root)
    status["dirty"] = bool(result.stdout.strip())

    result = _run_git(["remote", "get-url", _DEFAULT_REMOTE], repo_root)
    status["remote"] = result.stdout.strip() if result.returncode == 0 else None

    return status


def _fetch(repo_root: str) -> _GitResult:
    return _run_git(["fetch", "--all", "--prune"], repo_root)


def _tracking_counts(repo_root: str, status: dict) -> dict:
    """Fill in the upstream branch name and the ahead/behind counts."""
    result = _run_git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], repo_root
    )
    if result.returncode != 0:
        return status
    status["upstream"] = result.stdout.strip()

    result = _run_git(["rev-list", "--left-right", "--count", "HEAD...@{u}"], repo_root)
    if result.returncode == 0:
        parts = result.stdout.split()
        if len(parts) == 2:
            try:
                status["ahead"] = int(parts[0])
                status["behind"] = int(parts[1])
            except ValueError:
                pass
    return status


def _reinstall_dependencies(repo_root: str) -> _GitResult:
    """Reinstall requirements.txt with the interpreter that is running Sweepy."""
    return _install_requirements(repo_root, ["-r", "requirements.txt"])


def _install_requirements(repo_root: str, args: List[str]) -> _GitResult:
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pip", "install", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return _GitResult(returncode=127, stderr="pip was not found.")
    return _GitResult(completed.returncode, completed.stdout, completed.stderr)


def _reinstall_optional_engines(repo_root: str, engine_names: List[str]) -> _GitResult:
    """Reinstall the optional engines this checkout already had.

    A code pull can leave installed extras behind, so the update keeps them in
    step with the new code instead of silently dropping them.
    """
    from engine.engines import install_specs

    specs = install_specs(engine_names)
    if not specs:
        return _GitResult(returncode=0)
    return _install_requirements(repo_root, list(specs))


def _installed_optional_engines() -> List[str]:
    """Name the optional engines already present, ignoring the built-in ones."""
    try:
        from engine.engines import installed_engines

        return installed_engines(include_core=False)
    except Exception:  # an import problem must never block a code update
        return []


def check_for_updates(repo_root: Optional[str] = None) -> str:
    """Fetch and report whether a newer version exists, without changing anything."""
    repo_root = repo_root or _repo_root()
    status = gather_status(repo_root)
    if not status["is_repo"]:
        return "Sweepy is not installed from a Git repository, so it cannot update itself."
    if not status["remote"]:
        return "No Git remote named 'origin' is configured."

    _fetch(repo_root)
    status = _tracking_counts(repo_root, status)
    if status["upstream"] is None:
        return f"Branch '{status['branch']}' has no upstream branch to compare against."

    if status["behind"] == 0:
        return f"Sweepy is up to date (v{_read_version(repo_root)})."
    return (
        f"Update available: {status['behind']} new commit(s) behind "
        f"'{status['upstream']}'. Run 'python swee.py --update' to install it."
    )


def update_sweepy(repo_root: Optional[str] = None) -> str:
    """Pull the latest Sweepy code and reinstall dependencies when it is safe."""
    repo_root = repo_root or _repo_root()
    status = gather_status(repo_root)
    if not status["is_repo"]:
        return "Sweepy is not installed from a Git repository, so it cannot update itself."
    if not status["remote"]:
        return "No Git remote named 'origin' is configured."

    old_version = _read_version(repo_root)
    optional_engines = _installed_optional_engines()
    _fetch(repo_root)
    status = _tracking_counts(repo_root, status)
    if status["upstream"] is None:
        return f"Branch '{status['branch']}' has no upstream branch to compare against."
    if status["behind"] == 0:
        return f"Sweepy is already up to date (v{old_version})."
    if status["dirty"]:
        return (
            "Sweepy has local changes. Commit or stash them, then run "
            "'python swee.py --update' again."
        )
    if status["ahead"]:
        return (
            f"Branch '{status['branch']}' is {status['ahead']} commit(s) ahead of "
            f"'{status['upstream']}'. Push or reset before updating."
        )

    pull = _run_git(["pull", "--ff-only"], repo_root)
    if pull.returncode != 0:
        detail = pull.stderr.strip() or "git pull reported an error."
        return f"Update failed: {detail}"

    new_version = _read_version(repo_root)

    pip_result = _reinstall_dependencies(repo_root)
    if pip_result.returncode != 0:
        tail = (pip_result.stderr or pip_result.stdout or "pip reported an error.").strip()[-400:]
        return (
            f"Code updated to v{new_version}, but the dependency install failed. "
            f"Run 'python -m pip install -r requirements.txt' yourself. {tail}"
        )

    extras_note = ""
    if optional_engines:
        extras = _reinstall_optional_engines(repo_root, optional_engines)
        if extras.returncode != 0:
            extras_tail = (extras.stderr or extras.stdout or "pip reported an error.").strip()[-400:]
            extras_note = (
                f" Optional engines need a reinstall too: "
                f"{', '.join(optional_engines)}. {extras_tail}"
            )

    return f"Sweepy updated from v{old_version} to v{new_version}.{extras_note}"
