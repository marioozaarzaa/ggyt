from datetime import UTC, datetime

from ggyt_bot.backtesting.engine import run_backtest
from ggyt_bot.storage.database import TradingDatabase


def test_database_creates_required_tables(tmp_path) -> None:
    db = TradingDatabase(tmp_path / "trading.sqlite3")
    row_id = db.record("signals", {"symbol": "SPY", "signal": "BUY"})

    assert row_id == 1
    assert db.latest("signals", 1)[0]["symbol"] == "SPY"


def test_backtest_writes_outputs(tmp_path) -> None:
    result = run_backtest(
        symbol="SPY",
        start=datetime(2022, 1, 1, tzinfo=UTC),
        end=datetime(2022, 12, 31, tzinfo=UTC),
        strategy_name="sma",
        output_dir=tmp_path,
    )

    assert result.equity_curve
    assert list(tmp_path.glob("*.json"))
    assert list(tmp_path.glob("*.csv"))
    assert list(tmp_path.glob("*.svg"))
