from __future__ import annotations
from typing import Any
from ggyt_bot.jarvis.agents.base import JarvisAgent
from ggyt_bot.jarvis.llm import LLMInterface

class MarketingAgent(JarvisAgent):
    def __init__(self) -> None:
        super().__init__("Marketing Growth")
        self.llm = LLMInterface()

    def analyze(self, context: dict[str, Any]) -> str:
        task = context.get("task", "")
        prompt = f"Context: {context} | Task: {task}"
        system = "You are a growth hacker. Suggest viral marketing strategies and copy for ads."
        return self.llm.chat(prompt, system_prompt=system)
