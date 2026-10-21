from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from typing import Dict, List, Optional

log = logging.getLogger("sweepy.engine.session")


def stable_id(url: str) -> str:
    """Return a stable, content-addressed id for a job based on its URL."""
    return hashlib.sha1((url or "").encode("utf-8")).hexdigest()


class SweepSession:
    """Thread-safe store of card records keyed by their stable job id.

    Merge precedence is enforced by call order (later writes win):
        deterministic <- import_jobs <- submit_judgments
    """

    def __init__(self) -> None:
        self._jobs: Dict[str, dict] = {}
        self._order: List[str] = []
        self._lock = threading.Lock()

    def upsert(self, job: dict) -> None:
        """Insert or overwrite a single card record. Later writes win."""
        jid = job.get("id") or stable_id(job.get("url", ""))
        job = dict(job)
        job["id"] = jid
        with self._lock:
            if jid not in self._jobs:
                self._order.append(jid)
            self._jobs[jid] = job

    def set_many(self, jobs: List[dict]) -> None:
        for job in jobs:
            self.upsert(job)

    def get(self, job_id: str) -> Optional[dict]:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def all(self) -> List[dict]:
        with self._lock:
            return [dict(self._jobs[jid]) for jid in self._order]

    def apply_judgments(self, job_id: str, **fields) -> dict:
        """Merge non-None judgment overrides into an existing card."""
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(f"No job with id {job_id!r} in the session")
            job = self._jobs[job_id]
            for key, value in fields.items():
                if value is not None:
                    job[key] = value
            if fields.get("match_value") is not None:
                self._rerank()
            return dict(job)

    def _rerank(self) -> None:
        """Renumber ranks so a report sorted by rank matches the assessed scores.

        Assessment overwrites the deterministic overlap scores that produced the
        original ranks, so leaving the old numbers in place lets a report headed
        "Highest to Lowest Match %" list a 58% card above a 60% one. Cards that
        share a score keep their previous relative order.
        """
        ordered = sorted(
            self._jobs.values(),
            key=lambda job: (-int(job.get("match_value") or 0), int(job.get("rank") or 0)),
        )
        self._order = [job["id"] for job in ordered]
        for rank, job in enumerate(ordered, start=1):
            job["rank"] = rank
            # Page placement is derived from rank, so drop the previous labels.
            job.pop("page", None)
            job.pop("page_theme", None)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.all(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "SweepSession":
        session = cls()
        if not os.path.exists(path):
            return session
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, list):
            session.set_many(payload)
        elif isinstance(payload, dict):
            session.set_many(payload.get("jobs", []) or [])
        return session
