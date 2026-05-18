from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ggyt_bot.backtesting.engine import BacktestCosts, run_backtest
from ggyt_bot.backtesting.walkforward import run_walk_forward
from ggyt_bot.broker import AlpacaBroker, SimulatedBroker
from ggyt_bot.core.state_manager import StateManager
from ggyt_bot.dashboard.app import run_dashboard
from ggyt_bot.engine import TradingEngine
from ggyt_bot.execution.broker_mt5 import MT5Broker
from ggyt_bot.security.policy import LocalOnlyPolicy, enforce_local_only
from ggyt_bot.settings import BotConfig, RuntimeSettings
from ggyt_bot.state import BotState
from ggyt_bot.storage.database import TradingDatabase

app = typer.Typer(help="Local-only trading bot with Alpaca execution and strict risk stops.")
console = Console()
CONFIG_OPTION = typer.Option(Path("config/example.yaml"), help="YAML config path.")


def _load_engine(config_path: Path) -> tuple[TradingEngine, RuntimeSettings]:
    config = BotConfig.from_yaml(config_path)
    settings = RuntimeSettings()
    settings.validate_execution_safety()
    database = TradingDatabase(settings.ggyt_db_path)
    if settings.broker == "MT5":
        broker = MT5Broker(settings, database=database)
        broker.connect()
    elif settings.broker == "PAPER":
        broker = SimulatedBroker(
            {symbol: [100 + i * 0.1 for i in range(240)] for symbol in config.symbols}
        )
    else:
        broker = AlpacaBroker(settings)
    state = StateManager(settings.ggyt_state_path, broker, database).startup()
    return TradingEngine(broker, config, state, settings.ggyt_log_path, database), settings


@app.command()
def demo() -> None:
    """Run a local deterministic simulation without broker credentials."""
    config = BotConfig()
    prices = {"SPY": [100 + i * 0.2 for i in range(240)]}
    broker = SimulatedBroker(prices)
    database = TradingDatabase(Path("data/demo.sqlite3"))
    engine = TradingEngine(broker, config, BotState(), Path("logs/demo.jsonl"), database)
    _print_events(engine.run_once())


@app.command()
def once(config: Annotated[Path, CONFIG_OPTION]) -> None:
    """Run exactly one decision cycle."""
    engine, settings = _load_engine(config)
    events = engine.run_once()
    engine.state.save(settings.ggyt_state_path)
    _print_events(events)


@app.command()
def run(config: Annotated[Path, CONFIG_OPTION]) -> None:
    """Run continuously until interrupted or a risk stop halts the bot."""
    engine, settings = _load_engine(config)
    try:
        engine.run_forever()
    finally:
        engine.state.save(settings.ggyt_state_path)


@app.command()
def stop(reason: str = "manual stop") -> None:
    """Enable the local kill switch and stop future runs until the next safe rollover/reset."""
    settings = RuntimeSettings()
    state = BotState.load(settings.ggyt_state_path)
    state.kill_switch(reason)
    state.save(settings.ggyt_state_path)
    console.print(f"Kill switch enabled: {reason}")


@app.command()
def status() -> None:
    """Show local bot state and recent database events."""
    settings = RuntimeSettings()
    settings.validate_local_only()
    state = BotState.load(settings.ggyt_state_path)
    console.print(state)
    db = TradingDatabase(settings.ggyt_db_path)
    _print_events(db.latest("signals", 5))


@app.command()
def health() -> None:
    """Validate local-only and live-trading safety settings."""
    settings = RuntimeSettings()
    settings.validate_execution_safety()
    enforce_local_only(LocalOnlyPolicy(bind_host=settings.bind_host))
    console.print("Health OK: local-only policy and execution safety checks passed")


@app.command()
def dashboard(port: int = 8501) -> None:
    """Start Streamlit dashboard bound only to localhost/127.0.0.1."""
    settings = RuntimeSettings()
    settings.validate_local_only()
    run_dashboard(settings.ggyt_db_path, host="127.0.0.1", port=port)


@app.command()
def backtest(
    symbol: str = "SPY",
    from_date: str = typer.Option("2022-01-01", "--from"),
    to_date: str = typer.Option("2024-12-31", "--to"),
    strategy: str = "sma",
    walk_forward: bool = False,
    commission: float = 1.0,
    spread_bps: float = 2.0,
    slippage_bps: float = 3.0,
    latency_ms: int = 100,
    market_impact_bps: float = 1.0,
) -> None:
    """Run local backtest and save CSV, JSON and SVG equity curve under backtests/."""
    start = datetime.fromisoformat(from_date).replace(tzinfo=UTC)
    end = datetime.fromisoformat(to_date).replace(tzinfo=UTC)
    if walk_forward:
        results = run_walk_forward(symbol, strategy)
        for name, result in results.items():
            console.print(f"{name}: PnL={result.pnl:.2f} Sharpe={result.sharpe:.2f}")
        return
    result = run_backtest(
        symbol=symbol,
        start=start,
        end=end,
        strategy_name=strategy,
        costs=BacktestCosts(
            commission_per_trade=commission,
            spread_bps=spread_bps,
            slippage_bps=slippage_bps,
            latency_ms=latency_ms,
            market_impact_bps_per_100k=market_impact_bps,
        ),
    )
    console.print(
        f"PnL={result.pnl:.2f} Sharpe={result.sharpe:.2f} Sortino={result.sortino:.2f} "
        f"MaxDD={result.max_drawdown:.2%} PF={result.profit_factor:.2f} "
        f"Expectancy={result.expectancy:.2f} WinRate={result.win_rate:.2%}"
    )


@app.command("mt5-connect")
def mt5_connect() -> None:
    """Connect to the local MetaTrader 5 terminal and validate account/symbol safety."""
    settings = RuntimeSettings()
    database = TradingDatabase(settings.ggyt_db_path)
    broker = MT5Broker(settings, database=database)
    broker.connect()
    console.print("MT5 connected")


@app.command("mt5-status")
def mt5_status() -> None:
    """Show local MT5 account and connection status."""
    settings = RuntimeSettings()
    broker = MT5Broker(settings, database=TradingDatabase(settings.ggyt_db_path))
    broker.connect()
    console.print(broker.health_check())


@app.command("mt5-symbols")
def mt5_symbols() -> None:
    """Validate configured MT5 symbols and show market status."""
    settings = RuntimeSettings()
    broker = MT5Broker(settings, database=TradingDatabase(settings.ggyt_db_path))
    broker.connect()
    rows = [broker.get_market_status(symbol) for symbol in settings.mt5_allowed_symbols]
    _print_events([{**row, "type": "MT5_SYMBOL"} for row in rows])


@app.command("mt5-sync")
def mt5_sync() -> None:
    """Synchronize MT5 positions, orders, balance and equity into local storage."""
    settings = RuntimeSettings()
    broker = MT5Broker(settings, database=TradingDatabase(settings.ggyt_db_path))
    broker.connect()
    console.print(broker.sync())


@app.command("mt5-health")
def mt5_health() -> None:
    """Run MT5 watchdog-style health checks with optional local reconnect."""
    settings = RuntimeSettings()
    broker = MT5Broker(settings, database=TradingDatabase(settings.ggyt_db_path))
    broker.connect()
    console.print(broker.health_check())


def _print_events(events: list[dict[str, object]]) -> None:
    table = Table(title="Bot events")
    table.add_column("Type")
    table.add_column("Details")
    for event in events:
        event_type = str(event.get("type", event.get("event", "record")))
        details = ", ".join(
            f"{key}={value}" for key, value in event.items() if key not in {"ts", "type"}
        )
        table.add_row(event_type, details)
    console.print(table)


if __name__ == "__main__":
    app()
