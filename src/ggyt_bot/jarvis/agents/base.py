from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class JarvisAgent(ABC):
    """Base class for all Jarvis agents."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def analyze(self, context: dict[str, Any]) -> str:
        """Analyze the current context and provide an insight or recommendation."""
        ...
