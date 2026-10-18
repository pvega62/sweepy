from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Dict, Optional


class CircuitBreaker:
    """Track consecutive failures per source and refuse calls during a cooldown."""

    def __init__(self, failure_threshold: int = 5, cooldown: float = 30.0):
        self.failure_threshold = failure_threshold
        self.cooldown = cooldown
        self._failures: Dict[str, int] = defaultdict(int)
        self._last_failure: Dict[str, float] = {}
        self._lock = threading.Lock()

    def is_open(self, source: str) -> bool:
        with self._lock:
            if self._failures[source] < self.failure_threshold:
                return False
            if time.time() - self._last_failure.get(source, 0.0) < self.cooldown:
                return True
            self._failures[source] = 0
            return False

    def record_failure(self, source: str) -> None:
        with self._lock:
            self._failures[source] += 1
            self._last_failure[source] = time.time()

    def record_success(self, source: str) -> None:
        with self._lock:
            self._failures[source] = 0

    def failure_count(self, source: str) -> int:
        with self._lock:
            return self._failures[source]

    def snapshot(self) -> Dict[str, Dict[str, Optional[float]]]:
        with self._lock:
            return {
                name: {
                    "failures": count,
                    "last_failure": self._last_failure.get(name),
                    "open": count >= self.failure_threshold,
                }
                for name, count in self._failures.items()
            }

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()
            self._last_failure.clear()
