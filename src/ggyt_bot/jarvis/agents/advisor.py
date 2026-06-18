from __future__ import annotations
from typing import Any
from ggyt_bot.jarvis.agents.base import JarvisAgent
from ggyt_bot.jarvis.llm import LLMInterface

class FinancialAdvisorAgent(JarvisAgent):
    def __init__(self) -> None:
        super().__init__("Financial Advisor")
        self.llm = LLMInterface()

    def analyze(self, context: dict[str, Any]) -> str:
        task = context.get("task", "")
        if not task and "equity" not in context:
            return "Financial Advisor: Monitoring market conditions and account health."

        prompt = f"Context: {context} | Task: {task}"
        system = "You are a senior financial advisor. Analyze risk and suggest portfolio optimizations."
        return self.llm.chat(prompt, system_prompt=system)
