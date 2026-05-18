from __future__ import annotations

from pathlib import Path

from ggyt_bot.security.policy import LocalOnlyPolicy, enforce_local_only
from ggyt_bot.storage.database import TradingDatabase


def run_dashboard(db_path: Path, host: str = "127.0.0.1", port: int = 8501) -> None:
    policy = LocalOnlyPolicy(bind_host=host)
    enforce_local_only(policy)
    try:
        import streamlit.web.cli as stcli  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Streamlit is required for the dashboard. Run: pip install -e ."
        ) from exc
    import sys

    sys.argv = [
        "streamlit",
        "run",
        __file__,
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(port),
        "--",
        str(db_path),
    ]
    stcli.main()


def render(db_path: Path) -> None:
    try:
        import streamlit as st  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Streamlit is required for the dashboard. Run: pip install -e ."
        ) from exc

    db = TradingDatabase(db_path)
    st.title("GGYT Local Trading Bot")
    st.caption("Local-only dashboard: http://localhost:8501")
    cols = st.columns(4)
    latest_stats = db.latest("daily_stats", 1)
    stats = latest_stats[0] if latest_stats else {}
    cols[0].metric("Capital actual", stats.get("equity", "n/a"))
    cols[1].metric("PnL diario", stats.get("daily_pnl", "n/a"))
    cols[2].metric("PnL total", stats.get("total_pnl", "n/a"))
    cols[3].metric("Estado bot", stats.get("status", "unknown"))
    risk_cols = st.columns(3)
    risk_cols[0].metric("Riesgo usado", stats.get("risk_used", "n/a"))
    risk_cols[1].metric("Riesgo disponible", stats.get("risk_available", "n/a"))
    risk_cols[2].metric("Drawdown", stats.get("drawdown", "n/a"))
    st.subheader("Régimen de mercado")
    st.write(db.latest("market_conditions", 10))
    st.subheader("Posiciones abiertas")
    st.write(db.latest("positions", 20))
    st.subheader("Órdenes pendientes / recientes")
    st.write(db.latest("orders", 20))
    st.subheader("Señales")
    st.write(db.latest("signals", 20))
    st.subheader("Logs / errores")
    st.write(db.latest("errors", 20))


if __name__ == "__main__":
    import sys

    render(Path(sys.argv[-1]) if len(sys.argv) > 1 else Path("data/trading.sqlite3"))
