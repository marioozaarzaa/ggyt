from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ggyt_bot.data.feature_engine import build_features
from ggyt_bot.data.market_data import OHLCVSeries
from ggyt_bot.models import Signal
from ggyt_bot.strategies import STRATEGY_REGISTRY, SMAStrategy
from ggyt_bot.strategies.strategy_base import StrategyContext


@dataclass(frozen=True)
class BacktestCosts:
    commission_per_trade: float = 1.0
    spread_bps: float = 2.0
    slippage_bps: float = 3.0
    latency_ms: int = 100
    market_impact_bps_per_100k: float = 1.0


@dataclass(frozen=True)
class BacktestResult:
    symbol: str
    strategy: str
    pnl: float
    sharpe: float
    sortino: float
    max_drawdown: float
    profit_factor: float
    expectancy: float
    win_rate: float
    trades: int
    commission_paid: float
    estimated_spread_paid: float
    estimated_slippage_paid: float
    estimated_market_impact_paid: float
    latency_ms: int
    equity_curve: list[float]


def synthetic_prices(start: datetime, end: datetime) -> list[float]:
    days = max(260, (end - start).days or 260)
    return [100 + (index * 0.03) + math.sin(index / 7) * 2 for index in range(days)]


def run_backtest(
    *,
    symbol: str,
    start: datetime,
    end: datetime,
    strategy_name: str = "sma",
    output_dir: Path = Path("backtests"),
    costs: BacktestCosts | None = None,
) -> BacktestResult:
    costs = costs or BacktestCosts()
    closes = synthetic_prices(start, end)
    strategy_cls = STRATEGY_REGISTRY.get(strategy_name, SMAStrategy)
    strategy = strategy_cls()
    cash = 100_000.0
    shares = 0.0
    entry_price = 0.0
    wins: list[float] = []
    losses: list[float] = []
    equity_curve: list[float] = []
    returns: list[float] = []
    previous_equity = cash
    commission_paid = 0.0
    spread_paid = 0.0
    slippage_paid = 0.0
    market_impact_paid = 0.0
    for index in range(220, len(closes)):
        window = closes[: index + 1]
        series = OHLCVSeries.from_closes(symbol, window)
        context = StrategyContext(symbol, series, build_features(series))
        decision = strategy.generate_signal(context)
        price = closes[index]
        if decision.signal is Signal.BUY and shares == 0:
            notional = cash * 0.95
            execution_price, cost_breakdown = _apply_costs(price, notional, costs, side=1)
            shares = max(0.0, (notional - cost_breakdown["commission"]) / execution_price)
            cash -= notional
            entry_price = execution_price
            commission_paid += cost_breakdown["commission"]
            spread_paid += cost_breakdown["spread"]
            slippage_paid += cost_breakdown["slippage"]
            market_impact_paid += cost_breakdown["impact"]
        elif decision.signal is Signal.SELL and shares > 0:
            notional = shares * price
            execution_price, cost_breakdown = _apply_costs(price, notional, costs, side=-1)
            gross = shares * execution_price
            pnl = gross - shares * entry_price - cost_breakdown["commission"]
            if pnl >= 0:
                wins.append(pnl)
            else:
                losses.append(abs(pnl))
            cash += gross - cost_breakdown["commission"]
            shares = 0.0
            commission_paid += cost_breakdown["commission"]
            spread_paid += cost_breakdown["spread"]
            slippage_paid += cost_breakdown["slippage"]
            market_impact_paid += cost_breakdown["impact"]
        equity = cash + shares * price
        equity_curve.append(equity)
        returns.append((equity - previous_equity) / previous_equity if previous_equity else 0.0)
        previous_equity = equity
    if shares > 0:
        notional = shares * closes[-1]
        execution_price, cost_breakdown = _apply_costs(closes[-1], notional, costs, side=-1)
        pnl = shares * execution_price - shares * entry_price - cost_breakdown["commission"]
        (wins if pnl >= 0 else losses).append(abs(pnl))
        cash += shares * execution_price - cost_breakdown["commission"]
        commission_paid += cost_breakdown["commission"]
        spread_paid += cost_breakdown["spread"]
        slippage_paid += cost_breakdown["slippage"]
        market_impact_paid += cost_breakdown["impact"]
    pnl = cash - 100_000.0
    max_dd = _max_drawdown(equity_curve)
    sharpe = _sharpe(returns)
    sortino = _sortino(returns)
    profit_factor = sum(wins) / sum(losses) if losses else float("inf") if wins else 0.0
    trades = len(wins) + len(losses)
    expectancy = (sum(wins) - sum(losses)) / trades if trades else 0.0
    win_rate = len(wins) / trades if trades else 0.0
    result = BacktestResult(
        symbol=symbol,
        strategy=strategy_name,
        pnl=pnl,
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown=max_dd,
        profit_factor=profit_factor,
        expectancy=expectancy,
        win_rate=win_rate,
        trades=trades,
        commission_paid=commission_paid,
        estimated_spread_paid=spread_paid,
        estimated_slippage_paid=slippage_paid,
        estimated_market_impact_paid=market_impact_paid,
        latency_ms=costs.latency_ms,
        equity_curve=equity_curve,
    )
    save_backtest(result, output_dir)
    return result


def save_backtest(result: BacktestResult, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    stem = f"{result.symbol}_{result.strategy}_{stamp}"
    payload = result.__dict__.copy()
    (output_dir / f"{stem}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with (output_dir / f"{stem}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["index", "equity"])
        writer.writerows(enumerate(result.equity_curve))
    _write_svg_equity_curve(output_dir / f"{stem}.svg", result.equity_curve)


def _apply_costs(
    price: float, notional: float, costs: BacktestCosts, *, side: int
) -> tuple[float, dict[str, float]]:
    spread = notional * costs.spread_bps / 10_000
    slippage = notional * costs.slippage_bps / 10_000
    impact = notional * (costs.market_impact_bps_per_100k * (notional / 100_000)) / 10_000
    price_adjustment = (spread + slippage + impact) / max(notional / price, 1e-9)
    execution_price = price + (price_adjustment if side > 0 else -price_adjustment)
    return execution_price, {
        "commission": costs.commission_per_trade,
        "spread": spread,
        "slippage": slippage,
        "impact": impact,
    }


def _max_drawdown(equity_curve: list[float]) -> float:
    high = 0.0
    max_dd = 0.0
    for equity in equity_curve:
        high = max(high, equity)
        if high:
            max_dd = max(max_dd, (high - equity) / high)
    return max_dd


def _sharpe(returns: list[float]) -> float:
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((ret - mean) ** 2 for ret in returns) / (len(returns) - 1)
    return (mean / math.sqrt(variance) * math.sqrt(252)) if variance > 0 else 0.0


def _sortino(returns: list[float]) -> float:
    downside = [ret for ret in returns if ret < 0]
    if not downside:
        return 0.0
    mean = sum(returns) / len(returns)
    downside_dev = math.sqrt(sum(ret**2 for ret in downside) / len(downside))
    return (mean / downside_dev * math.sqrt(252)) if downside_dev > 0 else 0.0


def _write_svg_equity_curve(path: Path, equity_curve: list[float]) -> None:
    if not equity_curve:
        path.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
        return
    width, height = 900, 300
    low, high = min(equity_curve), max(equity_curve)
    span = high - low or 1.0
    step = width / max(1, len(equity_curve) - 1)
    points = [
        f"{index * step:.2f},{height - ((equity - low) / span * (height - 20)) - 10:.2f}"
        for index, equity in enumerate(equity_curve)
    ]
    path.write_text(
        "<svg xmlns='http://www.w3.org/2000/svg' width='900' height='300'>"
        "<polyline fill='none' stroke='green' stroke-width='2' points='"
        + " ".join(points)
        + "'/></svg>",
        encoding="utf-8",
    )
