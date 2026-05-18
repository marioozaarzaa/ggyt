from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class StrategyConfig:
    short_window: int = 20
    long_window: int = 50
    min_signal_strength: float = 0.001

    def __post_init__(self) -> None:
        if self.short_window < 2:
            raise ValueError("short_window must be >= 2")
        if self.long_window <= self.short_window:
            raise ValueError("long_window must be greater than short_window")
        if self.min_signal_strength < 0:
            raise ValueError("min_signal_strength must be >= 0")


@dataclass
class RiskConfig:
    max_position_notional_pct: float = 0.05
    max_total_exposure_pct: float = 0.15
    max_daily_loss_pct: float = 0.0025
    max_drawdown_pct: float = 0.005
    stop_on_any_loss: bool = True
    per_position_stop_loss_pct: float = 0.003
    liquidate_on_halt: bool = True
    max_risk_per_trade_pct: float = 0.005
    minimum_equity: float = 0.0

    def __post_init__(self) -> None:
        _check_range("max_position_notional_pct", self.max_position_notional_pct, 0, 0.25)
        _check_range("max_total_exposure_pct", self.max_total_exposure_pct, 0, 0.50)
        _check_range("max_daily_loss_pct", self.max_daily_loss_pct, 0, 0.10)
        _check_range("max_drawdown_pct", self.max_drawdown_pct, 0, 0.20)
        _check_range("per_position_stop_loss_pct", self.per_position_stop_loss_pct, 0, 0.20)
        _check_range("max_risk_per_trade_pct", self.max_risk_per_trade_pct, 0, 0.05)
        if self.minimum_equity < 0:
            raise ValueError("minimum_equity must be >= 0")


@dataclass
class ExecutionConfig:
    poll_seconds: int = 60
    extended_hours: bool = False
    min_cash_reserve_pct: float = 0.50
    trading_windows: list[str] = field(
        default_factory=lambda: ["09:45-11:30", "14:00-16:00"]
    )
    max_spread_pct: float = 0.002
    max_slippage_pct: float = 0.003
    avoid_open_minutes: int = 15
    avoid_close_minutes: int = 0

    def __post_init__(self) -> None:
        if self.poll_seconds < 10:
            raise ValueError("poll_seconds must be >= 10")
        _check_range("min_cash_reserve_pct", self.min_cash_reserve_pct, 0, 0.95, inclusive_min=True)
        _check_range("max_spread_pct", self.max_spread_pct, 0, 0.05)
        _check_range("max_slippage_pct", self.max_slippage_pct, 0, 0.05)
        if self.avoid_open_minutes < 0 or self.avoid_close_minutes < 0:
            raise ValueError("avoid market open/close minutes must be >= 0")


@dataclass
class BotConfig:
    symbols: list[str] = field(default_factory=lambda: ["SPY"])
    strategy_name: str = "sma"
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)

    def __post_init__(self) -> None:
        symbols = sorted({symbol.strip().upper() for symbol in self.symbols if symbol.strip()})
        if not symbols:
            raise ValueError("at least one symbol is required")
        self.symbols = symbols
        self.strategy_name = self.strategy_name.strip().lower()

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> BotConfig:
        return cls(
            symbols=list(raw.get("symbols", ["SPY"])),
            strategy_name=str(raw.get("strategy_name", "sma")),
            strategy=StrategyConfig(**raw.get("strategy", {})),
            risk=RiskConfig(**raw.get("risk", {})),
            execution=ExecutionConfig(**raw.get("execution", {})),
        )

    @classmethod
    def from_yaml(cls, path: Path) -> BotConfig:
        try:
            import yaml  # type: ignore[import-not-found]
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "PyYAML is required to load YAML config files. Run: pip install -e ."
            ) from exc
        with path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
        return cls.from_mapping(raw)


@dataclass
class RuntimeSettings:
    alpaca_api_key: str = field(default_factory=lambda: os.getenv("ALPACA_API_KEY", ""))
    alpaca_secret_key: str = field(default_factory=lambda: os.getenv("ALPACA_SECRET_KEY", ""))
    alpaca_paper: bool = field(default_factory=lambda: _env_bool("ALPACA_PAPER", True))
    ggyt_dry_run: bool = field(default_factory=lambda: _env_bool("GGYT_DRY_RUN", True))
    ggyt_allow_live_trading: bool = field(
        default_factory=lambda: _env_bool("GGYT_ALLOW_LIVE_TRADING", False)
    )
    ggyt_state_path: Path = field(
        default_factory=lambda: Path(os.getenv("GGYT_STATE_PATH", "state.json"))
    )
    ggyt_log_path: Path = field(
        default_factory=lambda: Path(os.getenv("GGYT_LOG_PATH", "logs/trades.jsonl"))
    )
    ggyt_db_path: Path = field(
        default_factory=lambda: Path(os.getenv("GGYT_DB_PATH", "data/trading.sqlite3"))
    )
    broker: str = field(default_factory=lambda: os.getenv("BROKER", "ALPACA").upper())
    mt5_login: str = field(default_factory=lambda: os.getenv("MT5_LOGIN", ""))
    mt5_password: str = field(default_factory=lambda: os.getenv("MT5_PASSWORD", ""))
    mt5_server: str = field(default_factory=lambda: os.getenv("MT5_SERVER", ""))
    mt5_terminal_path: str = field(default_factory=lambda: os.getenv("MT5_TERMINAL_PATH", ""))
    mt5_magic_number: int = field(default_factory=lambda: _env_int("MT5_MAGIC_NUMBER", 888888))
    mt5_timeout: int = field(default_factory=lambda: _env_int("MT5_TIMEOUT", 60000))
    mt5_max_slippage: int = field(default_factory=lambda: _env_int("MT5_MAX_SLIPPAGE", 10))
    mt5_max_spread_pct: float = field(
        default_factory=lambda: _env_float("MT5_MAX_SPREAD_PCT", 0.003)
    )
    mt5_default_risk_percent: float = field(
        default_factory=lambda: _env_float("MT5_DEFAULT_RISK_PERCENT", 0.005)
    )
    mt5_auto_reconnect: bool = field(default_factory=lambda: _env_bool("MT5_AUTO_RECONNECT", True))
    mt5_allowed_symbols: list[str] = field(
        default_factory=lambda: _env_csv("MT5_ALLOWED_SYMBOLS", "EURUSD,XAUUSD,GBPUSD,US100")
    )
    ggyt_confirm_mt5_account: str = field(
        default_factory=lambda: os.getenv("GGYT_CONFIRM_MT5_ACCOUNT", "")
    )
    run_mode: str = field(default_factory=lambda: os.getenv("RUN_MODE", "LOCAL_ONLY"))
    allow_remote: bool = field(default_factory=lambda: _env_bool("ALLOW_REMOTE", False))
    allow_webhooks: bool = field(default_factory=lambda: _env_bool("ALLOW_WEBHOOKS", False))
    allow_external_commands: bool = field(
        default_factory=lambda: _env_bool("ALLOW_EXTERNAL_COMMANDS", False)
    )
    bind_host: str = field(default_factory=lambda: os.getenv("GGYT_BIND_HOST", "127.0.0.1"))
    ggyt_confirm_live_account_id: str = field(
        default_factory=lambda: os.getenv("GGYT_CONFIRM_LIVE_ACCOUNT_ID", "")
    )
    ggyt_live_confirmation: str = field(
        default_factory=lambda: os.getenv("GGYT_LIVE_CONFIRMATION", "")
    )

    def validate_local_only(self) -> None:
        from ggyt_bot.security.policy import LocalOnlyPolicy, enforce_local_only

        enforce_local_only(
            LocalOnlyPolicy(
                run_mode=self.run_mode,
                allow_remote=self.allow_remote,
                allow_webhooks=self.allow_webhooks,
                allow_external_commands=self.allow_external_commands,
                bind_host=self.bind_host,
            )
        )

    def validate_execution_safety(self) -> None:
        self.validate_local_only()
        if self.broker not in {"ALPACA", "MT5", "PAPER"}:
            raise ValueError("BROKER must be ALPACA, MT5, or PAPER")
        if not self.alpaca_paper and not self.ggyt_allow_live_trading:
            raise ValueError(
                "Live trading is blocked. Set GGYT_ALLOW_LIVE_TRADING=true only after "
                "paper testing, understanding the code, and accepting the risk."
            )
        if not self.ggyt_dry_run and (not self.alpaca_api_key or not self.alpaca_secret_key):
            raise ValueError("API keys are required when GGYT_DRY_RUN=false")
        if not self.alpaca_paper and not self.ggyt_confirm_live_account_id:
            raise ValueError("GGYT_CONFIRM_LIVE_ACCOUNT_ID is required for live trading")
        if not self.alpaca_paper and self.ggyt_live_confirmation != "I_ACCEPT_LIVE_TRADING_RISK":
            raise ValueError("GGYT_LIVE_CONFIRMATION=I_ACCEPT_LIVE_TRADING_RISK is required")
        if self.broker == "MT5" and not self.ggyt_dry_run and not self.ggyt_allow_live_trading:
            raise ValueError("MT5 live order routing requires GGYT_ALLOW_LIVE_TRADING=true")
        if self.broker == "MT5" and not self.ggyt_dry_run and not self.ggyt_confirm_mt5_account:
            raise ValueError("GGYT_CONFIRM_MT5_ACCOUNT is required for MT5 live order routing")


def _check_range(
    name: str,
    value: float,
    minimum: float,
    maximum: float,
    *,
    inclusive_min: bool = False,
) -> None:
    lower_ok = value >= minimum if inclusive_min else value > minimum
    if not lower_ok or value > maximum:
        operator = ">=" if inclusive_min else ">"
        raise ValueError(f"{name} must be {operator} {minimum} and <= {maximum}")


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def _env_csv(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip().upper() for item in raw.split(",") if item.strip()]


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return float(value)
