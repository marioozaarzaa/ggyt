from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ggyt_bot.backtesting.engine import BacktestResult, run_backtest


def run_walk_forward(
    symbol: str,
    strategy_name: str,
    output_dir: Path = Path("backtests"),
) -> dict[str, BacktestResult]:
    """Fixed train/validation/forward split to reduce overfitting risk."""
    return {
        "train_2022_2024": run_backtest(
            symbol=symbol,
            start=datetime(2022, 1, 1, tzinfo=UTC),
            end=datetime(2024, 12, 31, tzinfo=UTC),
            strategy_name=strategy_name,
            output_dir=output_dir,
        ),
        "validation_2025": run_backtest(
            symbol=symbol,
            start=datetime(2025, 1, 1, tzinfo=UTC),
            end=datetime(2025, 12, 31, tzinfo=UTC),
            strategy_name=strategy_name,
            output_dir=output_dir,
        ),
        "forward_2026": run_backtest(
            symbol=symbol,
            start=datetime(2026, 1, 1, tzinfo=UTC),
            end=datetime(2026, 12, 31, tzinfo=UTC),
            strategy_name=strategy_name,
            output_dir=output_dir,
        ),
    }
