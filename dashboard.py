"""
AI Governance Console — Premium Dashboard
Design system: Cyber-Governance Console (Stitch)
"""
import hashlib
import json
import sqlite3
import time
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Page config — must be first Streamlit call
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Governance Console",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Cyber-Governance Design System CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
.stApp {
    background-color: #0d1117;
    color: #dae3ee;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #0b141c !important;
    border-right: 1px solid #21262d;
}
[data-testid="stSidebar"] * { color: #dae3ee !important; }

/* ── Metric Cards (glassmorphism) ── */
[data-testid="stMetric"] {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 20px 24px !important;
    transition: border-color 0.2s, box-shadow 0.2s;
}
[data-testid="stMetric"]:hover {
    border-color: #00d4aa;
    box-shadow: 0 0 12px 0 rgba(0,212,170,0.2);
}
[data-testid="stMetricLabel"] > div {
    color: #8b949e !important;
    font-size: 12px !important;
    font-weight: 500;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
[data-testid="stMetricValue"] > div {
    color: #f0f6fc !important;
    font-size: 32px !important;
    font-weight: 700 !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
}

/* ── Buttons ── */
.stButton > button {
    background: #00d4aa !important;
    color: #0d1117 !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 8px 20px !important;
    transition: opacity 0.2s, box-shadow 0.2s !important;
}
.stButton > button:hover {
    opacity: 0.85 !important;
    box-shadow: 0 0 10px rgba(0,212,170,0.4) !important;
}

/* ── Inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
.stChatInput textarea {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    color: #f0f6fc !important;
    border-radius: 6px !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stChatInput"] {
    background-color: transparent !important;
}
[data-testid="stChatInput"] > div {
    background-color: #161b22 !important;
    border-color: #30363d !important;
}
[data-testid="stBottomBlockContainer"] {
    background-color: #0d1117 !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #00d4aa !important;
    box-shadow: 0 0 8px rgba(0,212,170,0.3) !important;
}

/* ── Toggle ── */
[data-testid="stToggle"] span[data-checked="true"] {
    background-color: #da3633 !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    margin-bottom: 8px;
}

/* ── Dividers ── */
hr { border-color: #21262d !important; }

/* ── Success / Error / Warning override ── */
.stSuccess { background: rgba(35,134,54,0.15) !important; border: 1px solid #238636 !important; border-radius: 6px !important; }
.stError   { background: rgba(218,54,51,0.15) !important; border: 1px solid #da3633 !important; border-radius: 6px !important; }
.stWarning { background: rgba(210,153,34,0.15) !important; border: 1px solid #d29922 !important; border-radius: 6px !important; }
.stInfo    { background: rgba(0,212,170,0.08) !important;  border: 1px solid #00d4aa33 !important; border-radius: 6px !important; }

/* ── Custom component styles ── */
.console-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 0 4px 0;
}
.shield-icon { font-size: 28px; }
.console-title {
    font-size: 26px;
    font-weight: 700;
    color: #f0f6fc;
    margin: 0;
    line-height: 1.2;
}
.console-subtitle {
    font-size: 13px;
    color: #8b949e;
    margin: 2px 0 0 0;
    letter-spacing: 0.02em;
}
.status-badge-active {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(35,134,54,0.15);
    border: 1px solid #238636;
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 600;
    color: #3fb950;
}
.status-badge-killed {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(218,54,51,0.15);
    border: 1px solid #da3633;
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 600;
    color: #f85149;
}
.pulse {
    width: 8px; height: 8px;
    background: #3fb950;
    border-radius: 50%;
    animation: pulse 2s infinite;
    display: inline-block;
}
@keyframes pulse {
    0%,100% { box-shadow: 0 0 0 0 rgba(63,185,80,0.5); }
    50%      { box-shadow: 0 0 0 5px rgba(63,185,80,0); }
}
.section-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 16px;
}
.section-title {
    font-size: 14px;
    font-weight: 600;
    color: #f0f6fc;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    margin: 0 0 14px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}
.pill-approved {
    background: rgba(35,134,54,0.2);
    border: 1px solid #238636;
    color: #3fb950;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
}
.pill-blocked {
    background: rgba(218,54,51,0.2);
    border: 1px solid #da3633;
    color: #f85149;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
}
.pill-pending {
    background: rgba(210,153,34,0.2);
    border: 1px solid #d29922;
    color: #e3b341;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
}
.hash-text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #00d4aa;
    letter-spacing: 0.02em;
}
.req-id-text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #8b949e;
}
.review-item {
    background: #0d1117;
    border: 1px solid #d2992240;
    border-left: 3px solid #d29922;
    border-radius: 6px;
    padding: 12px 14px;
    margin-bottom: 10px;
}
.review-item-id {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #e3b341;
    font-weight: 500;
}
.review-item-rule {
    font-size: 12px;
    color: #8b949e;
    margin-top: 2px;
}
.test-result-approved {
    background: rgba(35,134,54,0.1);
    border: 1px solid #238636;
    border-radius: 6px;
    padding: 14px;
    margin-top: 12px;
}
.test-result-blocked {
    background: rgba(218,54,51,0.1);
    border: 1px solid #da3633;
    border-radius: 6px;
    padding: 14px;
    margin-top: 12px;
}
.result-status-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.result-content {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: #8b949e;
    word-break: break-all;
}
.integrity-verified {
    background: rgba(0,212,170,0.08);
    border: 1px solid #00d4aa40;
    border-radius: 6px;
    padding: 12px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: #00d4aa;
    text-align: center;
    letter-spacing: 0.04em;
}
.sidebar-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 0 20px 0;
}
.sidebar-brand-text {
    font-size: 15px;
    font-weight: 700;
    color: #f0f6fc;
}
.kill-switch-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #8b949e;
    margin-bottom: 6px;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# State helpers
# ─────────────────────────────────────────────────────────────────────────────
STATE_PATH = "config/state.json"
API_BASE   = "http://localhost:8000"


def _read_state() -> dict:
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {"kill_switch_active": False}


def _write_state(active: bool) -> None:
    state = {
        "kill_switch_active": active,
        "last_toggled_by": "dashboard-operator",
        "last_toggled_at": datetime.now(timezone.utc).isoformat(),
    }
    import os; os.makedirs("config", exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def _load_ledger(query: str) -> pd.DataFrame:
    try:
        conn = sqlite3.connect("ledger.db")
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


def _ledger_counts() -> tuple[int, int, int, int]:
    try:
        conn = sqlite3.connect("ledger.db")
        total   = conn.execute("SELECT COUNT(*) FROM compliance_log").fetchone()[0]
        blocked = conn.execute("SELECT COUNT(*) FROM compliance_log WHERE action_taken='BLOCKED'").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM compliance_log WHERE review_status='PENDING_REVIEW'").fetchone()[0]
        conn.close()
        return total, total - blocked, blocked, pending
    except Exception:
        return 0, 0, 0, 0


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
current_state = _read_state()
is_active     = current_state.get("kill_switch_active", False)

with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <span style="font-size:24px">🛡️</span>
        <span class="sidebar-brand-text">AI Governance</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**Navigation**")
    st.caption("📊 Dashboard — Active")
    if st.button("↻ Refresh Dashboard"):
        st.rerun()
    st.markdown("---")

    # Status badge
    if is_active:
        st.markdown('<div class="status-badge-killed">⛔ KILL SWITCH ACTIVE</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-badge-active"><span class="pulse"></span> System Operational</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="kill-switch-label">Emergency Control</div>', unsafe_allow_html=True)

    kill_switch = st.toggle(
        "Global Kill Switch",
        value=is_active,
        help="Halts ALL inbound AI requests immediately. Returns 503 to all callers.",
    )
    if kill_switch != is_active:
        _write_state(kill_switch)
        st.rerun()

    st.markdown("---")
    toggled_at = current_state.get("last_toggled_at", "Never")
    if toggled_at != "Never":
        try:
            dt = datetime.fromisoformat(toggled_at)
            toggled_at = dt.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            pass
    st.caption(f"Last toggled: {toggled_at}")
    st.caption(f"Auto-refresh: 5s")

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
header_left, header_right = st.columns([3, 1])

with header_left:
    st.markdown("""
    <div class="console-header">
        <span class="shield-icon">🛡️</span>
        <div>
            <p class="console-title">AI Governance Console</p>
            <p class="console-subtitle">Runtime Firewall &nbsp;·&nbsp; Cryptographic Audit Ledger &nbsp;·&nbsp; EU AI Act Compliant</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

with header_right:
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("🔍 Run Integrity Check", use_container_width=True):
        try:
            from src.database import verify_chain_integrity
            intact, broken_at = verify_chain_integrity()
            if intact:
                st.markdown('<div class="integrity-verified">✔ CHAIN INTEGRITY VERIFIED</div>', unsafe_allow_html=True)
            else:
                st.error(f"⛔ CHAIN BROKEN at row {broken_at}")
        except Exception as e:
            st.error(f"Verification error: {e}")

if kill_switch:
    st.error("⛔ KILL SWITCH ACTIVE — All AI requests are frozen. No prompts are being processed.", icon="⛔")
else:
    st.success("✅ Runtime Firewall: Active | All systems nominal", icon="✅")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# Metric Cards
# ─────────────────────────────────────────────────────────────────────────────
total, passed, blocked, pending = _ledger_counts()

c1, c2, c3, c4 = st.columns(4)
c1.metric("🔢 Total Requests",   total)
c2.metric("✅ Approved",          passed,  delta=f"+{passed}"  if passed  else None)
c3.metric("🚫 Blocked",           blocked, delta=f"-{blocked}" if blocked else None, delta_color="inverse")
c4.metric("⏳ Pending Review",    pending, delta=f"{pending} awaiting" if pending else "Queue clear")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# Main Content — Audit Ledger + Right Panel
# ─────────────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([3, 2])

# ── Left: Cryptographic Audit Chain ──
with col_left:
    st.markdown('<div class="section-title">🔗 Cryptographic Audit Chain Ledger</div>', unsafe_allow_html=True)

    df = _load_ledger("""
        SELECT
            id,
            substr(request_id, 1, 18) || '...'  AS request_id,
            tenant_id,
            action_taken,
            COALESCE(rule_violated, '—')         AS rule_violated,
            review_status,
            substr(current_hash, 1, 14) || '…'  AS hash_preview
        FROM compliance_log
        ORDER BY id DESC
        LIMIT 100
    """)

    if df.empty:
        st.info("🛰️ No audit entries yet. Send a prompt via the Prompt Tester or API to generate records.")
    else:
        # Colour-code action column
        def style_action(val):
            if val == "BLOCKED":
                return "background-color: rgba(218,54,51,0.15); color: #f85149; font-weight:600;"
            elif val == "APPROVED":
                return "background-color: rgba(35,134,54,0.15); color: #3fb950; font-weight:600;"
            return ""

        styled = df.style.map(style_action, subset=["action_taken"])
        st.dataframe(
            styled,
            use_container_width=True,
            height=340,
            column_config={
                "id":           st.column_config.NumberColumn("ID", width="small"),
                "request_id":   st.column_config.TextColumn("Request ID"),
                "tenant_id":    st.column_config.TextColumn("Tenant"),
                "action_taken": st.column_config.TextColumn("Action"),
                "rule_violated":st.column_config.TextColumn("Rule Violated"),
                "review_status":st.column_config.TextColumn("Review"),
                "hash_preview": st.column_config.TextColumn("Hash (SHA-256)"),
            },
            hide_index=True,
        )

# ── Right: Review Queue + Live Prompt Tester ──
with col_right:

    # Review Queue
    st.markdown('<div class="section-title">⏳ Human Review Queue & HITL Triggers</div>', unsafe_allow_html=True)

    df_review = _load_ledger("""
        SELECT request_id, rule_violated, action_taken
        FROM compliance_log
        WHERE review_status = 'PENDING_REVIEW'
        ORDER BY id DESC
        LIMIT 10
    """)

    if df_review.empty:
        st.markdown('<div style="background:#161b22;border:1px solid #238636;border-radius:6px;padding:10px 14px;font-size:13px;color:#3fb950;">✔ Queue clear — no items pending review</div>', unsafe_allow_html=True)
    else:
        from src.database import update_review_status
        st.warning(f"{len(df_review)} item(s) flagged for human review or HITL authorization")
        for _, row in df_review.iterrows():
            rid   = str(row.get("request_id", "—"))
            rid_display = rid[:22] + "..."
            rule  = str(row.get("rule_violated", "—"))
            action = str(row.get("action_taken", "—"))
            is_hitl = action == "PENDING_HITL"
            icon = "🛑 HITL PAUSE:" if is_hitl else "⚠ REVIEW:"
            color = "#f85149" if is_hitl else "#e3b341"
            
            with st.container():
                rc1, rc2, rc3 = st.columns([6, 2, 2])
                with rc1:
                    st.markdown(f"""
                    <div class="review-item" style="margin-bottom:0;">
                        <div class="review-item-id" style="color:{color}">{icon} {rid_display}</div>
                        <div class="review-item-rule">{rule}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with rc2:
                    if st.button("✅ Approve", key=f"approve_{rid}", use_container_width=True):
                        update_review_status(rid, "APPROVED")
                        st.rerun()
                with rc3:
                    if st.button("❌ Reject", key=f"reject_{rid}", use_container_width=True):
                        update_review_status(rid, "REJECTED")
                        st.rerun()
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    st.markdown("---")

    # Live Prompt Tester
    st.markdown('<div class="section-title">⚡ Live Prompt Tester</div>', unsafe_allow_html=True)
    st.caption("Test prompts against the live firewall API in real time.")

    test_prompt = st.text_area(
        "Prompt",
        placeholder="e.g. How do I write malware?",
        label_visibility="collapsed",
        height=80,
        key="test_prompt_input",
    )

    if st.button("▶ Test Prompt", use_container_width=True):
        if not test_prompt.strip():
            st.warning("Enter a prompt first.")
        else:
            try:
                resp = requests.post(
                    f"{API_BASE}/v1/intercept",
                    json={"prompt": test_prompt},
                    timeout=5,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    pii  = data.get("pii_redacted", [])
                    st.markdown(f"""
                    <div class="test-result-approved">
                        <div class="result-status-label" style="color:#3fb950">✅ APPROVED</div>
                        <div class="result-content">Request ID: {data.get("request_id","—")}</div>
                        <div class="result-content" style="color:#8b949e">{data.get("explanation", "")}</div>
                        {'<div class="result-content">PII Scrubbed: ' + ', '.join(pii) + '</div>' if pii else ''}
                        <div class="result-content" style="margin-top:6px;color:#dae3ee">{data.get("llm_response","—")}</div>
                    </div>
                    """, unsafe_allow_html=True)
                elif resp.status_code == 403:
                    try:
                        detail = resp.json().get("detail", "Policy violation")
                    except Exception:
                        detail = resp.text
                    
                    is_hitl = "HITL" in detail
                    status_label = "🛑 PENDING HITL AUTHORIZATION" if is_hitl else "🚫 BLOCKED — 403 Forbidden"
                    color = "#d29922" if is_hitl else "#f85149"
                    st.markdown(f"""
                    <div class="test-result-blocked" style="border-color:{color}">
                        <div class="result-status-label" style="color:{color}">{status_label}</div>
                        <div class="result-content">{detail}</div>
                    </div>
                    """, unsafe_allow_html=True)
                elif resp.status_code == 503:
                    st.error("Kill switch is active — all requests blocked (503)")
                else:
                    st.error(f"Unexpected response: {resp.status_code}")
            except requests.ConnectionError:
                st.error("⚠ Cannot reach API. Start uvicorn on port 8000 first.")
            except Exception as e:
                st.error(f"Error: {e}")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# ❤️ Responsible AI Health Report
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">❤️ Responsible AI Health Report</div>', unsafe_allow_html=True)
st.caption("Fairness, Transparency, and Human-in-the-loop accountability metrics generated directly from the immutable ledger.")

try:
    from src.ethics.transparency_report import generate_health_report
    health = generate_health_report()
    hc1, hc2, hc3, hc4 = st.columns(4)
    hc1.metric("Fairness Score", f"{health.get('fairness_score', 100)}%")
    hc2.metric("Total Requests", health.get("total", 0))
    hc3.metric("Blocked/Unsafe", health.get("blocked", 0))
    hc4.metric("HITL Pauses", health.get("hitl", 0))
except Exception as e:
    st.error(f"Failed to load RAI metrics: {e}")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# Regulatory AI Assistant
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">🤖 Regulatory AI Assistant</div>', unsafe_allow_html=True)
st.caption("Ask about EU AI Act, NIST AI RMF, ISO 42001, or GDPR. Powered by local embeddings — no API key required.")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_q := st.chat_input("e.g. What does Article 12 of the EU AI Act require?"):
    st.session_state.chat_history.append({"role": "user", "content": user_q})
    with st.chat_message("user"):
        st.markdown(user_q)

    with st.chat_message("assistant"):
        with st.spinner("Searching regulatory corpus..."):
            try:
                from src.rag import build_index, query_policy
                build_index()
                answer = query_policy(user_q)
            except Exception as e:
                answer = (
                    f"RAG index unavailable. Ensure `sentence-transformers` and `chromadb` "
                    f"are installed and restart the dashboard. Error: {e}"
                )
        st.markdown(answer)
    st.session_state.chat_history.append({"role": "assistant", "content": answer})

# Auto-refresh removed to prevent blocking RAG embeddings
