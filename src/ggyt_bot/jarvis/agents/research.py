from __future__ import annotations
from typing import Any
from ggyt_bot.jarvis.agents.base import JarvisAgent

class ResearchAgent(JarvisAgent):
    """Agent specialized in deep research, web browsing, and reporting."""
    def __init__(self) -> None:
        super().__init__("Deep Researcher")

    def analyze(self, context: dict[str, Any]) -> str:
        task = context.get("task", "")
        if "research" in task.lower() or "info" in task.lower() or "report" in task.lower():
            return "Research Agent: Browsing the web for the latest reports. I will compile a summary via Perplexity/Manus."
        return "Research Agent: Continuously scanning for new data points in your interest sectors."
