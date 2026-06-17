from __future__ import annotations

from typing import Any
from ggyt_bot.jarvis.agents.base import JarvisAgent


class FinancialAdvisorAgent(JarvisAgent):
    """An agent that provides high-level financial advice based on market conditions."""

    def __init__(self) -> None:
        super().__init__("Financial Advisor")

    def analyze(self, context: dict[str, Any]) -> str:
        regime = context.get("regime", "unknown")
        volatility = context.get("volatility") or 0.0
        equity = context.get("equity") or 0.0

        if regime == "PANIC":
            return f"Capital protection is priority. Equity at {equity:.2f}. Suggesting immediate risk reduction."

        if volatility > 0.05:
            return "High volatility detected. Reduce position sizing to maintain portfolio stability."

        if regime == "TRENDING":
            return "Positive trend alignment. Good time for disciplined momentum trades."

        return f"Market is {regime}. Portfolio equity is {equity:.2f}. Monitoring for optimal entry points."
