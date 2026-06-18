from __future__ import annotations
from typing import Any
from ggyt_bot.jarvis.agents.base import JarvisAgent
from ggyt_bot.jarvis.llm import LLMInterface

class CryptoAgent(JarvisAgent):
    def __init__(self) -> None:
        super().__init__("Crypto Specialist")
        self.llm = LLMInterface()

    def analyze(self, context: dict[str, Any]) -> str:
        task = context.get("task", "")
        if "crypto" not in str(context).lower() and "btc" not in str(context).lower():
            return "Crypto Specialist: Monitoring blockchain trends."

        prompt = f"Context: {context} | Task: {task}"
        system = "You are a crypto expert. Analyze tokens, degen plays, and DeFi yield opportunities."
        return self.llm.chat(prompt, system_prompt=system)
