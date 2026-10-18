import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Keep every test off the real cache and away from the user's last-profile pointer."""
    monkeypatch.setenv("SWEEPY_CACHE_PATH", str(tmp_path / "sweepy-cache.db"))

    import engine.config as config

    monkeypatch.setattr(
        config, "_LAST_PROFILE_FILE", str(tmp_path / "profiles" / ".last_profile")
    )
