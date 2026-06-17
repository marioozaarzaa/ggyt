from __future__ import annotations
from typing import Any
from ggyt_bot.jarvis.agents.base import JarvisAgent

class ProgrammingAgent(JarvisAgent):
    """Agent specialized in programming, debugging, and system architecture."""
    def __init__(self) -> None:
        super().__init__("Programming Specialist")

    def analyze(self, context: dict[str, Any]) -> str:
        task = context.get("task", "")
        if "bug" in task.lower() or "error" in task.lower():
            return "Programming Agent: Ready to debug. Please provide the log or code snippet."
        if "program" in task.lower() or "code" in task.lower():
            return "Programming Agent: I can help architect this. Suggesting a modular Python approach."
        return "Programming Agent: Monitoring codebase health and waiting for development tasks."
