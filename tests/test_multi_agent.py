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
    resp = orchestrator.process_task("I have a bug in my code")
    assert "Programming Agent: Ready to debug" in resp

    # Test Crypto routing
    resp = orchestrator.process_task("Analyze crypto BTC")
    assert "Crypto Agent: Scanning Solana/Ethereum" in resp

    # Test unknown routing
    resp = orchestrator.process_task("What is the weather?")
    assert "I'm not sure which agent can handle that best" in resp

    # Verify persistence of tasks
    tasks = db.latest("jarvis_memory", 10)
    assert any(t.get("category") == "user_task" for t in tasks)
