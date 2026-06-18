from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path("workspace")

class JarvisActionExecutor:
    """Executes physical actions in the local workspace, such as writing files or running scripts."""

    def __init__(self, workspace_path: Path = WORKSPACE_ROOT) -> None:
        self.workspace = workspace_path
        self.workspace.mkdir(parents=True, exist_ok=True)

    def write_file(self, filename: str, content: str) -> str:
        """Writes a file to the workspace."""
        try:
            file_path = self.workspace / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Action Success: File '{filename}' created in workspace."
        except Exception as e:
            return f"Action Error: Could not write file: {str(e)}"

    def list_workspace(self) -> list[str]:
        """Lists files in the workspace."""
        return [str(p.relative_to(self.workspace)) for p in self.workspace.rglob("*") if p.is_file()]

    def run_script(self, filename: str) -> str:
        """Runs a python script from the workspace (local-only safety)."""
        file_path = self.workspace / filename
        if not file_path.exists():
            return f"Action Error: File '{filename}' not found."

        try:
            result = subprocess.run(
                ["python", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            return f"Action Output:\n{result.stdout}\nErrors:\n{result.stderr}"
        except Exception as e:
            return f"Action Error: Execution failed: {str(e)}"

    def publish_github(self, repo_name: str, files: list[str]) -> str:
        """Publishes files to GitHub Pages (requires JARVIS_GITHUB_TOKEN)."""
        token = os.getenv("JARVIS_GITHUB_TOKEN")
        if not token:
            return "Action Error: JARVIS_GITHUB_TOKEN not found."

        try:
            from github import Github
            g = Github(token)
            user = g.get_user()

            # Create or get repo
            try:
                repo = user.create_repo(repo_name, auto_init=True)
            except:
                repo = user.get_repo(repo_name)

            for filename in files:
                file_path = self.workspace / filename
                if not file_path.exists(): continue
                with open(file_path, "r") as f:
                    content = f.read()

                try:
                    contents = repo.get_contents(filename)
                    repo.update_file(contents.path, f"Update {filename}", content, contents.sha)
                except:
                    repo.create_file(filename, f"Initial commit {filename}", content)

            # Enable Pages if not enabled
            # Note: PyGithub doesn't have a direct "enable pages" for personal repos easily
            # but pushing index.html to main usually triggers it if configured.
            return f"Action Success: Published to https://{user.login}.github.io/{repo_name}/"
        except Exception as e:
            return f"Action Error: GitHub publish failed: {str(e)}"
