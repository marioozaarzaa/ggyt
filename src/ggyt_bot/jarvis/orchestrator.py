from __future__ import annotations

import logging
from typing import Any

from ggyt_bot.jarvis.memory import MemoryManager
from ggyt_bot.storage.database import TradingDatabase

logger = logging.getLogger(__name__)

class JarvisOrchestrator:
    """The central brain of Jarvis, coordinating agents and managing memory."""

    def __init__(self, database: TradingDatabase) -> None:
        self.memory = MemoryManager(database)
        self.agents = []
        self.personality = "Professional Financial Advisor & Autonomous Executor"

    def register_agent(self, agent: Any) -> None:
        self.agents.append(agent)
        logger.info(f"Jarvis: Agent {agent.name} registered.")

    def think(self, context: dict[str, Any]) -> str:
        """Process current context and return Jarvis's thoughts/decisions."""
        insights = []
        for agent in self.agents:
            thought = agent.analyze(context)
            insights.append(thought)

        combined_thought = " | ".join(insights)
        # We don't store here to avoid redundancy with engine's event logging
        return combined_thought

    def process_task(self, task: str, context: dict[str, Any] | None = None) -> str:
        """Route a specific task to the best suited agent and return their response."""
        full_context = context or {}
        full_context["task"] = task

        responses = []
        for agent in self.agents:
            # Simple keyword matching for routing (can be improved with LLM)
            response = agent.analyze(full_context)
            # Filter out non-responses
            if "Monitoring" not in response and "Standing by" not in response and "Researching" not in response:
                responses.append(response)

        if not responses:
            return "Jarvis: I'm not sure which agent can handle that best. Let me research it for you."

        final_response = " | ".join(responses)
        self.memory.store_insight("user_task", final_response, {"task": task})
        return final_response

    def get_status(self) -> str:
        return f"Jarvis is active with {len(self.agents)} agents. Mode: {self.personality}"
