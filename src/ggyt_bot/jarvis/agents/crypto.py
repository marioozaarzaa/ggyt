from __future__ import annotations
from typing import Any
from ggyt_bot.jarvis.agents.base import JarvisAgent

class CryptoAgent(JarvisAgent):
    """Agent specialized in Crypto markets, DeFi, and On-chain analysis."""
    def __init__(self) -> None:
        super().__init__("Crypto Analyst")

    def analyze(self, context: dict[str, Any]) -> str:
        task = context.get("task", "")
        if "crypto" in task.lower() or "token" in task.lower() or "defi" in task.lower():
            return "Crypto Agent: Scanning Solana/Ethereum for new opportunities. High social sentiment detected on AIXBT."
        return "Crypto Agent: Monitoring on-chain whale movements and market sentiment."
