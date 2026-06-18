from __future__ import annotations
import json
from typing import Any
from ggyt_bot.jarvis.agents.base import JarvisAgent
from ggyt_bot.jarvis.llm import LLMInterface

class WebCreationAgent(JarvisAgent):
    """Agent specialized in autonomous web generation and sales landing pages."""

    def __init__(self) -> None:
        super().__init__("Web Factory")
        self.llm = LLMInterface()

    def analyze(self, context: dict[str, Any]) -> str:
        task = context.get("task", "")
        if not task:
            return "Web Factory: Monitoring for opportunities to generate high-conversion websites."

        # System prompt to force high-quality Tailwind output
        system_prompt = """
        You are the Jarvis Web Factory. Your goal is to generate professional, high-conversion landing pages.
        Always use Tailwind CSS (via CDN) for styling.
        The output must include an [ACTION: {"type": "write_file", "params": {"filename": "index.html", "content": "..."}}] block.
        Make the design modern, responsive, and oriented towards sales.
        """

        response = self.llm.chat(task, system_prompt=system_prompt)
        return response

    def get_template(self, niche: str) -> str:
        """Returns a base Tailwind template for a specific niche."""
        templates = {
            "restaurante": "<!-- Modern Restaurant Template -->",
            "gym": "<!-- High Energy Gym Template -->",
            "lawyer": "<!-- Professional Legal Template -->"
        }
        return templates.get(niche.lower(), "<!-- Generic Business Template -->")
