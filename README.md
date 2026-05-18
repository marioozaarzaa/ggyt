# GGYT Trading Bot

Sistema local de trading algorítmico en Python para Alpaca con ejecución **paper/live**, arquitectura modular, controles de riesgo estrictos, recuperación automática, SQLite, auditoría JSONL, backtesting y dashboard local.

> **Aviso importante:** esto no es asesoramiento financiero ni garantiza beneficios. No existe trading “sin casi riesgo”. El sistema está diseñado para ejecución local, paper trading, pruebas y reducción de daños operativos; no elimina riesgo de mercado, liquidez, slippage, fallos de broker/API, datos, configuración ni bugs.

## Principios de diseño

1. **Seguridad:** dry-run y paper por defecto; live requiere doble confirmación.
2. **Local-only:** sin VPS, cloud workers, webhooks externos, sockets públicos ni APIs remotas.
3. **Estabilidad:** estado persistente, recuperación al arrancar y watchdog.
4. **Mantenibilidad:** módulos separados por core, data, strategies, risk, execution, portfolio, storage y dashboard.
5. **Riesgo antes que rentabilidad:** kill switch, drawdown, pérdida diaria, sizing por ATR y límites de exposición.

## Arquitectura

```text
src/ggyt_bot/
├── core/              # engine wrapper, scheduler local, state manager, watchdog
├── data/              # market data, indicadores, feature engine
├── strategies/        # plugins: SMA, momentum, trend, mean reversion
├── risk/              # drawdown, daily limit, exposure, position sizing, RiskManager
├── execution/         # broker Alpaca, broker simulado/paper, order manager
├── portfolio/         # PortfolioManager
├── storage/           # SQLite + tablas + migraciones + auditoría
├── dashboard/         # Streamlit local-only en 127.0.0.1
├── backtesting/       # backtest y walk-forward
├── security/          # política LOCAL_ONLY
└── credentials/       # keyring OS + fallback local
```

Flujo principal:

```text
CLI local
  └── RuntimeSettings.validate_execution_safety()
        └── LocalOnlyPolicy(RUN_MODE=LOCAL_ONLY, bind_host=127.0.0.1)
  └── StateManager.startup()
        ├── load_state()
        ├── sync_positions()
        ├── sync_orders()
        ├── recover_open_positions()
        └── resume_engine()
  └── TradingEngine.run_once/run_forever()
        ├── Broker Alpaca / SimulatedBroker
        ├── FeatureEngine: EMA, RSI, MACD, ATR, volumen relativo
        ├── Strategy plugin
        ├── RiskManager + ATR sizing
        ├── OrderManager/Broker
        ├── SQLite storage
        └── JSONL audit log
```

## Instalación local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
```

Configura `.env` empezando siempre con paper + dry-run:

```bash
ALPACA_PAPER=true
GGYT_DRY_RUN=true
GGYT_ALLOW_LIVE_TRADING=false
GGYT_CONFIRM_LIVE_ACCOUNT_ID=
RUN_MODE=LOCAL_ONLY
ALLOW_REMOTE=false
ALLOW_WEBHOOKS=false
ALLOW_EXTERNAL_COMMANDS=false
GGYT_BIND_HOST=127.0.0.1
```

## Modo local obligatorio

El bot valida una política local-only antes de ejecución real:

- `RUN_MODE=LOCAL_ONLY`
- `ALLOW_REMOTE=false`
- `ALLOW_WEBHOOKS=false`
- `ALLOW_EXTERNAL_COMMANDS=false`
- dashboard/API local siempre en `127.0.0.1`
- nunca `0.0.0.0`

El proyecto no registra webhooks, sockets públicos, APIs remotas ni comandos externos.

## Seguridad de live trading

Live trading está bloqueado salvo que se cumplan simultáneamente:

```bash
ALPACA_PAPER=false
GGYT_ALLOW_LIVE_TRADING=true
GGYT_CONFIRM_LIVE_ACCOUNT_ID=<id exacto de tu cuenta Alpaca>
```

Además, el broker compara `broker.account.id` con `GGYT_CONFIRM_LIVE_ACCOUNT_ID`. Si no coincide, lanza `SecurityError` y no opera.

## Credenciales

No se recomienda guardar claves reales en `.env`. El módulo `CredentialStore` intenta usar primero el almacén seguro del sistema operativo:

- Windows Credential Manager
- macOS Keychain
- Linux Secret Service

Si no está disponible, usa fallback local con permisos restrictivos para desarrollo. Para producción local real, instala/configura `keyring` y usa el almacén del sistema.

## Comandos CLI

```bash
ggyt-bot demo
ggyt-bot once --config config/example.yaml
ggyt-bot run --config config/example.yaml
ggyt-bot stop "motivo"
ggyt-bot status
ggyt-bot health
ggyt-bot dashboard
ggyt-bot backtest --symbol SPY --from 2022-01-01 --to 2024-12-31 --strategy sma
ggyt-bot backtest --symbol SPY --strategy trend --walk-forward
```

> El script instalado se llama `ggyt-bot` por compatibilidad con el scaffold inicial.

## Estrategias plugin

Todas las estrategias implementan `StrategyBase` con:

- `name`
- `parameters`
- `generate_signal()`
- `validate_signal()`

Plugins incluidos:

- `sma`: mantiene la estrategia SMA original.
- `multi_indicator_trend`: regla profesional inicial.
- `momentum`: alias/plugin momentum sobre el motor multi-indicador.
- `trend`: alias/plugin trend.
- `mean_reversion`: RSI oversold/overbought.

Regla inicial multi-indicador:

```text
BUY si:
EMA20 > EMA50
AND EMA50 > EMA200
AND RSI > 45
AND RSI < 65
AND relative_volume > 1

SELL si:
EMA20 < EMA50
OR stop/riesgo excedido
```

Indicadores disponibles:

- EMA20
- EMA50
- EMA200
- RSI
- MACD
- ATR
- Volumen relativo

## Gestión de riesgo

Controles implementados:

- `stop_on_any_loss`
- límite de pérdida diaria
- límite de drawdown
- límite de exposición total
- máximo riesgo por trade
- stop por posición
- reserva mínima de caja
- minimum equity
- kill switch global
- liquidación opcional al halt

Sizing por riesgo:

```text
riesgo_por_trade = equity * 0.005
distancia_stop = ATR * 2
shares = riesgo_por_trade / distancia_stop
```

El notional final queda limitado además por cash disponible, buying power, reserva mínima, exposición total y tamaño máximo por posición.

## Persistencia

SQLite es el almacenamiento principal. JSONL se mantiene como auditoría append-only.

Tablas SQLite:

- `trades`
- `orders`
- `signals`
- `positions`
- `daily_stats`
- `errors`
- `backtests`

Ruta por defecto:

```bash
GGYT_DB_PATH=data/trading.sqlite3
```

## Recuperación automática

Al arrancar se ejecuta:

```python
startup()
load_state()
sync_positions()
sync_orders()
recover_open_positions()
resume_engine()
```

Esto permite sobrevivir mejor a reinicio del PC, cierre inesperado o excepción crítica, conservando estado en `state.json`, SQLite y JSONL.

## Watchdog

`SafetyWatchdog` puede parar el motor si:

- `market_data_age > 60`
- `api_errors > 5`
- `drawdown > limit`
- `account_equity < minimum`

Si se dispara un stop crítico, el motor puede liquidar posiciones con `panic_flatten()` cuando `liquidate_on_halt=true`.

## Backtesting y walk-forward

Backtesting local:

```bash
ggyt-bot backtest --symbol SPY --from 2022-01-01 --to 2024-12-31 --strategy sma
```

Walk-forward:

```bash
ggyt-bot backtest --symbol SPY --strategy trend --walk-forward
```

Fases por defecto:

- Entrenamiento: 2022-2024
- Validación: 2025
- Forward: 2026

Métricas:

- Sharpe ratio
- Sortino
- Max drawdown
- Profit factor
- Expectancy
- Win rate
- PnL

Resultados en `backtests/`:

- CSV equity curve
- JSON métricas
- SVG equity curve

## Dashboard local

```bash
ggyt-bot dashboard
```

URL:

```text
http://localhost:8501
```

El dashboard fuerza `127.0.0.1` y muestra:

- capital actual
- PnL diario
- riesgo usado/disponible
- posiciones abiertas
- órdenes recientes
- estado del bot
- señales
- logs/errores

## Configuración

Edita `config/example.yaml`:

```yaml
symbols: ["SPY", "QQQ"]
strategy_name: "multi_indicator_trend"
risk:
  max_position_notional_pct: 0.05
  max_total_exposure_pct: 0.15
  max_daily_loss_pct: 0.0025
  max_drawdown_pct: 0.005
  stop_on_any_loss: true
  per_position_stop_loss_pct: 0.003
  liquidate_on_halt: true
  max_risk_per_trade_pct: 0.005
execution:
  min_cash_reserve_pct: 0.50
```

## Pruebas

```bash
PYTHONPATH=src ruff check .
PYTHONPATH=src pytest -q
```

La meta de cobertura mínima es 80%; instala dependencias dev completas y ejecuta:

```bash
pytest --cov=ggyt_bot --cov-fail-under=80
```

## Riesgos y límites

- Ninguna estrategia garantiza profit.
- Los stops pueden tener slippage.
- Si la API o la red fallan, las órdenes pueden no ejecutarse como esperas.
- Paper trading no reproduce perfectamente la ejecución real.
- Activa live solo tras semanas/meses de pruebas, revisión de logs y auditoría del código.
