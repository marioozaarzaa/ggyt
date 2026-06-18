from __future__ import annotations
import pytest
from pathlib import Path
from ggyt_bot.jarvis.orchestrator import JarvisOrchestrator
from ggyt_bot.jarvis.agents.programming import ProgrammingAgent
from ggyt_bot.jarvis.agents.crypto import CryptoAgent
from ggyt_bot.storage.database import TradingDatabase

def test_multi_agent_routing(tmp_path):
    db_path = tmp_path / "test_multi.sqlite3"
    db = TradingDatabase(db_path)
    orchestrator = JarvisOrchestrator(db)

    orchestrator.register_agent(ProgrammingAgent())
    orchestrator.register_agent(CryptoAgent())

    # Test Programming routing
    resp = orchestrator.process_task("write some code")
    assert "ACTION" in resp
    assert "write_file" in resp

    # Test Crypto routing
    resp = orchestrator.process_task("Analyze crypto BTC")
    assert "Local Mode" in resp

    # Test unknown routing (should still be handled by LLM if agents are active)
    resp = orchestrator.process_task("What is the weather?")
    assert "Local Mode" in resp

    # Verify persistence of tasks
    tasks = db.latest("jarvis_memory", 10)
    assert len(tasks) > 0
    assert any("task" in str(t).lower() for t in tasks)
