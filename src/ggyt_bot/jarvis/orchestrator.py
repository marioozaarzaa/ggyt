from __future__ import annotations

import logging
from typing import Any

from ggyt_bot.jarvis.actions import JarvisActionExecutor
from ggyt_bot.jarvis.memory import MemoryManager
from ggyt_bot.storage.database import TradingDatabase

logger = logging.getLogger(__name__)

class JarvisOrchestrator:
    """The central brain of Jarvis, coordinating agents and managing memory."""

    def __init__(self, database: TradingDatabase) -> None:
        self.memory = MemoryManager(database)
        self.actions = JarvisActionExecutor()
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
            # Try to extract and queue actions
            self._parse_and_queue_actions(thought)

        combined_thought = " | ".join(insights)
        return combined_thought

    def _parse_and_queue_actions(self, text: str) -> None:
        import re
        import json
        # Extract [ACTION: {"type": "...", "params": {}}] - Supporting multi-line JSON
        matches = re.findall(r"\[ACTION:\s*(\{.*?\})\s*\]", text, re.DOTALL)
        for match in matches:
            try:
                # Clean up potential markdown or spacing
                clean_json = match.strip()
                action_data = json.loads(clean_json)
                self.memory.database.record("jarvis_memory", {
                    "type": "action",
                    "status": "pending",
                    "thought": text[:150].replace("\n", " ") + "...",
                    "details": action_data
                })
                logger.info(f"Jarvis: Action queued: {action_data.get('type')}")
            except (json.JSONDecodeError, AttributeError) as e:
                logger.error(f"Jarvis: Failed to parse action JSON: {e}")
                continue

    def execute_action(self, action_type: str, params: dict[str, Any]) -> str:
        """Executes a physical action in the workspace."""
        if action_type == "write_file":
            return self.actions.write_file(params.get("filename", "untitled.txt"), params.get("content", ""))
        if action_type == "run_script":
            return self.actions.run_script(params.get("filename", ""))
        if action_type == "publish_github":
            return self.actions.publish_github(params.get("repo_name", "my-web"), params.get("files", ["index.html"]))
        return f"Jarvis: Unknown action type {action_type}"

    def process_task(self, task: str, context: dict[str, Any] | None = None) -> str:
        """Route a specific task to the best suited agent and return their response."""
        full_context = context or {}
        full_context["task"] = task
        full_context["can_execute"] = True # Inform agents they can request actions

        responses = []
        for agent in self.agents:
            # Simple keyword matching for routing (can be improved with LLM)
            response = agent.analyze(full_context)
            # Filter out non-responses
            if "Monitoring" not in response and "Standing by" not in response and "Researching" not in response:
                responses.append(response)
                self._parse_and_queue_actions(response)

        if not responses:
            return "Jarvis: I'm not sure which agent can handle that best. Let me research it for you."

        final_response = " | ".join(responses)
        # Marked as processed if we are returning immediately to a request
        self.memory.store_insight("insight", final_response, {"task": task, "processed": True})
        return final_response

    def get_status(self) -> str:
        return f"Jarvis is active with {len(self.agents)} agents. Mode: {self.personality}"
