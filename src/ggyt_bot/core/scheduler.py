from __future__ import annotations

import time
from collections.abc import Callable


class LocalScheduler:
    """Simple local-only scheduler; no sockets, webhooks, workers, or remote control."""

    def __init__(self, interval_seconds: int) -> None:
        if interval_seconds < 1:
            raise ValueError("interval_seconds must be >= 1")
        self.interval_seconds = interval_seconds
        self._stopped = False

    def stop(self) -> None:
        self._stopped = True

    def run(self, callback: Callable[[], None]) -> None:
        while not self._stopped:
            callback()
            time.sleep(self.interval_seconds)
