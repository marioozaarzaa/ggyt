from __future__ import annotations
from typing import Any
from ggyt_bot.jarvis.agents.base import JarvisAgent

class WebCreationAgent(JarvisAgent):
    """Agent specialized in web development, React, Next.js, and SaaS interfaces."""
    def __init__(self) -> None:
        super().__init__("Web Builder")

    def analyze(self, context: dict[str, Any]) -> str:
        task = context.get("task", "")
        if "web" in task.lower() or "app" in task.lower() or "saas" in task.lower():
            if "create" in task.lower() or "build" in task.lower():
                return "Web Builder: Scaffolding a basic landing page in 'workspace/index.html'. [ACTION: write_file(filename='index.html', content='<h1>Jarvis SaaS</h1>')] "
            return "Web Builder: I can generate a Next.js/Tailwind scaffold for your new project."
        return "Web Builder: Standing by to design interfaces or deploy web components."
