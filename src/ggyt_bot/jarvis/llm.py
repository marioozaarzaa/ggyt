from __future__ import annotations

import os
from typing import Any

class LLMInterface:
    """Unified interface for interacting with LLM providers."""

    def __init__(self, provider: str = "mock") -> None:
        self.provider = provider
        self.api_key = os.getenv("JARVIS_LLM_API_KEY", "")

    def chat(self, prompt: str, system_prompt: str = "You are Jarvis, a helpful autonomous system.") -> str:
        """Sends a prompt to the configured LLM provider."""
        if self.provider == "mock":
            # Keyword-based mock for basic local testing
            # Look specifically at the 'Task:' part of the prompt if present
            task_part = prompt.split("Task:")[-1].lower() if "Task:" in prompt else prompt.lower()

            if "code" in task_part or "write" in task_part:
                return 'I will create that for you. [ACTION: {"type": "write_file", "params": {"filename": "new_logic.py", "content": "print(\'Jarvis Logic\')"}}]'
            if "run" in task_part or "exec" in task_part:
                return 'Executing script now. [ACTION: {"type": "run_script", "params": {"filename": "new_logic.py"}}]'
            return f"Jarvis ({self.provider}): I have processed your request: {prompt[:30]}"

        if not self.api_key:
            return "Error: JARVIS_LLM_API_KEY not set. Please provide a key to use real LLM agents."

        # REAL INTEGRATION SCALFOLD
        if self.provider == "openai":
            # try: import openai; ...
            return f"OpenAI Integration: Sending {len(prompt)} chars to GPT-4o..."

        return f"Jarvis LLM: Integration logic for {self.provider} should be added in llm.py"

    def generate_action(self, task: str) -> dict[str, Any]:
        """Parses a natural language task into a structured Jarvis action."""
        # This would use an LLM to extract JSON actions
        return {"action": "none", "params": {}}
