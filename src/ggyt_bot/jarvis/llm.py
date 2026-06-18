from __future__ import annotations

import os
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

class LLMInterface:
    """Unified interface for interacting with LLM providers (Local-first)."""

    def __init__(self, provider: str | None = None) -> None:
        # Default to environment or auto-detect
        self.provider = provider or os.getenv("JARVIS_LLM_PROVIDER", "ollama")
        self.api_key = os.getenv("JARVIS_LLM_API_KEY", "")
        self.base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.getenv("JARVIS_MODEL", "llama3.2:3b")

    def chat(self, prompt: str, system_prompt: str = "You are Jarvis, a highly efficient autonomous agent.") -> str:
        """Sends a prompt to the configured LLM provider with local fallback."""

        if self.provider == "ollama":
            try:
                import ollama
                response = ollama.chat(model=self.model, messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': prompt},
                ])
                return response['message']['content']
            except Exception as e:
                logger.warning(f"Ollama not available: {e}. Falling back to internal logic.")
                # If ollama fails, we don't return immediately, we try next provider or internal

        if self.api_key and self.provider in ["openai", "groq"]:
            # Placeholder for real API calls
            return f"Jarvis ({self.provider}): Real API integration would process: {prompt[:30]}"

        # Robust Internal Logic (The "Smart Mock")
        return self._internal_fallback(prompt)

    def _internal_fallback(self, prompt: str) -> str:
        """Smart fallback when no LLM is reachable."""
        p = prompt.lower()

        # Web Generation Logic
        if "web" in p or "html" in p or "landing" in p or "code" in p:
            niche = "Business"
            if "restaurante" in p: niche = "Restaurante"
            if "peluquería" in p: niche = "Peluquería"

            content = f"<!-- Tailwind Web --> <div class='bg-blue-600 text-white p-10'><h1>{niche} Pro</h1><p>The best in town.</p></div>"
            return f"I have designed a landing page for {niche}. [ACTION: {{\"type\": \"write_file\", \"params\": {{\"filename\": \"index.html\", \"content\": \"{content}\"}}}}]"

        if "lead" in p or "maps" in p or "buscar" in p:
            return """I am scanning Google Maps for businesses without websites.
            [ACTION: {"type": "run_script", "params": {"filename": "scrapers/maps_leads.py"}}]
            I will notify you once I find potential clients."""

        return f"Jarvis (Local Mode): I understand you want to: '{prompt[:50]}...'. I am standing by for autonomous execution."

    def generate_action(self, task: str) -> dict[str, Any]:
        """Parses a natural language task into a structured Jarvis action."""
        # In a real scenario, this uses the LLM with a JSON schema.
        # For now, we rely on the chat extraction.
        return {"action": "none", "params": {}}
