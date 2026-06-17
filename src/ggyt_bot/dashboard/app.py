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

    st.sidebar.title("Jarvis Terminal")
    jarvis_mode = st.sidebar.selectbox("Modo Jarvis", ["Asesor", "Autónomo"])
    st.sidebar.info(f"Jarvis está en modo: {jarvis_mode}")

    workspace_path = Path("workspace")
    if workspace_path.exists():
        st.sidebar.subheader("📁 Workspace")
        files = list(workspace_path.rglob("*"))
        for f in files:
            if f.is_file():
                st.sidebar.text(f"📄 {f.name}")

    st.subheader("🧠 Jarvis Memory & Insights")
    all_memory = db.latest("jarvis_memory", 20)

    # Filter memory vs actions
    insights = [m for m in all_memory if m.get("type") != "action"]
    actions = [m for m in all_memory if m.get("type") == "action"]

    tab1, tab2 = st.tabs(["Insights & Memory", "Action History"])

    with tab1:
        for insight in insights:
            with st.expander(f"💡 {insight.get('created_at')}"):
                st.write(f"**Thought:** {insight.get('thought')}")
                st.json(insight)

    with tab2:
        for action in actions:
            with st.expander(f"🎬 {action.get('created_at')} - {action.get('thought')}"):
                st.json(action.get("details", {}))

    st.divider()
    user_input = st.text_input("🎙️ Habla con Jarvis (Comandos de voz simulados)")
    if user_input:
        st.write(f"**Usuario:** {user_input}")
        # In a real app, we would have access to the engine's jarvis instance here.
        # For the dashboard demo, we simulate the routing logic or look it up in history.
        st.write(f"**Jarvis:** Entendido, procesando '{user_input}'...")

        # Simulation of task processing for the UI
        if "crypto" in user_input.lower():
            st.success("Crypto Agent: Scanning Solana/Ethereum for new opportunities. High social sentiment detected on AIXBT.")
        elif "code" in user_input.lower() or "program" in user_input.lower():
            st.success("Programming Agent: I can help architect this. Suggesting a modular Python approach.")
        elif "web" in user_input.lower():
            st.success("Web Builder: I can generate a Next.js/Tailwind scaffold for your new project.")
        elif "marketing" in user_input.lower():
            st.success("Marketing Agent: Analyzing target demographics. I can automate an email campaign.")
        elif "research" in user_input.lower():
            st.success("Research Agent: Browsing the web for the latest reports via Perplexity/Manus.")
        else:
            st.info("Jarvis: Tarea recibida. Mis agentes especializados están trabajando en ello.")

        # Show pending actions from DB
        pending_actions = [a for a in actions if a.get("status") == "pending"]
        for pending in pending_actions:
            st.warning(f"⚠️ Acción pendiente: {pending.get('details', {}).get('type')} - {pending.get('thought')}")
            if st.button(f"Aprobar y Ejecutar #{pending['id']}", key=f"approve_{pending['id']}"):
                # Update status in DB
                db._conn.execute("UPDATE jarvis_memory SET payload = ? WHERE id = ?", (
                    json.dumps({**pending, "status": "approved"}), pending["id"]
                ))
                db._conn.commit()
                st.balloons()
                st.success("Acción aprobada para ejecución.")
                st.rerun()


if __name__ == "__main__":
    import sys

    render(Path(sys.argv[-1]) if len(sys.argv) > 1 else Path("data/trading.sqlite3"))
