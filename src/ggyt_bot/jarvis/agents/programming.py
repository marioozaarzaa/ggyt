from __future__ import annotations
from typing import Any
from ggyt_bot.jarvis.agents.base import JarvisAgent
from ggyt_bot.jarvis.llm import LLMInterface

class ProgrammingAgent(JarvisAgent):
    """Agent specialized in programming, debugging, and system architecture."""
    def __init__(self) -> None:
        super().__init__("Programming Specialist")
        self.llm = LLMInterface(provider="mock")

    def analyze(self, context: dict[str, Any]) -> str:
        task = context.get("task", "")
        if not task:
            return "Programming Agent: Monitoring codebase health and waiting for development tasks."

        # Route to LLM for smarter reasoning and structured action generation
        return self.llm.chat(f"Context: {context} | Task: {task}")
