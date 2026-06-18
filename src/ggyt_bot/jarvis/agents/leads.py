from __future__ import annotations
from typing import Any
from ggyt_bot.jarvis.agents.base import JarvisAgent
from ggyt_bot.jarvis.llm import LLMInterface

class LeadGeneratorAgent(JarvisAgent):
    """Agent focused on finding clients without websites on Google Maps."""

    def __init__(self) -> None:
        super().__init__("Lead Engine")
        self.llm = LLMInterface()

    def analyze(self, context: dict[str, Any]) -> str:
        task = context.get("task", "")
        if "lead" in task.lower() or "buscar" in task.lower() or "cliente" in task.lower():
            # In a real app, this would use Playwright to scrape Maps
            return """Lead Engine: Scanning Google Maps for businesses in the specified area.
            [ACTION: {"type": "run_script", "params": {"filename": "scrapers/maps_leads.py"}}]
            I am looking for 'Restaurant', 'Dentist', 'Gym' with 'No website' labels.
            """
        return "Lead Engine: Standing by. Tell me which sector and city to target."
