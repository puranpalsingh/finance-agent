"""
CreditFlow — Finance Credit Follow-Up Email Agent
Streamlit UI that calls backend services directly (no HTTP layer needed).
"""

import os, sys, time, io
from pathlib import Path
from datetime import datetime, date

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ── Path setup so we can import backend services ────────────────
BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from services.data_ingestion import parse_csv_file, parse_upload
from services.email_generator import generate_email
from services.email_sender import send_email
from services.audit_logger import log_action, get_all_logs, get_sent_today_count

# ── Constants ────────────────────────────────────────────────────
DEFAULT_CSV = BACKEND_DIR / "data" / "invoices.csv"
DATA_DIR    = BACKEND_DIR / "data"

STAGE_COLOR = {
    "Stage 1": "#4ade80",
    "Stage 2": "#facc15",
    "Stage 3": "#fb923c",
    "Stage 4": "#f87171",
    "Escalated": "#c084fc",
    "Current": "#60a5fa",
}
STAGE_TONE = {
    "Stage 1": "Warm & Friendly",
    "Stage 2": "Polite but Firm",
    "Stage 3": "Formal & Serious",
    "Stage 4": "Stern & Urgent",
    "Escalated": "🚨 Manual Review",
    "Current": "Not Overdue",
}

# ── Page config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="CreditFlow · Collections Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────
css_path = BACKEND_DIR / "style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

# Extra inline CSS for fine-grained control
st.markdown("""
<style>
.brand-header {
    display:flex; align-items:center; gap:0.75rem;
    padding:1rem 0 0.5rem 0; border-bottom:1px solid rgba(139,154,183,0.12);
    margin-bottom:1.25rem;
}
.brand-icon {
    width:38px; height:38px; border-radius:8px;
    background:linear-gradient(135deg,#d97706,#f59e0b);
    display:flex; align-items:center; justify-content:center;
    font-size:1.2rem; flex-shrink:0;
}
.brand-title { font-size:1.1rem; font-weight:800; color:#fbbf24; letter-spacing:-0.02em; line-height:1; }
.brand-sub   { font-size:0.62rem; color:#64748b; letter-spacing:0.12em; font-family:'JetBrains Mono',monospace; margin-top:2px; }
.stage-badge {
    display:inline-block; padding:2px 10px; border-radius:4px;
    font-size:0.72rem; font-weight:600; font-family:'JetBrains Mono',monospace;
}
.tone-chip {
    display:inline-block; padding:2px 8px; border-radius:20px;
    font-size:0.68rem; font-family:'JetBrains Mono',monospace;
}
.stat-delta { font-size:0.7rem; color:#64748b; font-family:'JetBrains Mono',monospace; }
.section-title {
    font-size:0.7rem; font-weight:700; letter-spacing:0.1em;
    text-transform:uppercase; color:#64748b;
    font-family:'JetBrains Mono',monospace;
    margin-bottom:0.5rem;
}
.email-box {
    background:#111827; border:1px solid rgba(139,154,183,0.15);
    border-radius:8px; padding:1rem 1.1rem;
}
.email-subject { font-weight:700; font-size:1rem; color:#e2e8f0; margin-bottom:0.75rem; }
.email-body { font-family:'JetBrains Mono',monospace; font-size:0.8rem; color:#94a3b8; white-space:pre-wrap; line-height:1.8; }
.blocked-banner {
    background:rgba(168,85,247,0.1); border:1px solid rgba(168,85,247,0.35);
    border-radius:6px; padding:0.75rem 1rem; margin:0.5rem 0;
    color:#c084fc; font-family:'JetBrains Mono',monospace; font-size:0.82rem;
}
.audit-row { border-bottom:1px solid rgba(139,154,183,0.08); padding:0.5rem 0; }
div[data-testid="column"] { gap:0 !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ──────────────────────────────────────────────────────
def fmt_inr(n):
    return f"₹{int(n):,}"

def fmt_date(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d %b %Y")
    except Exception:
        return str(d)

def stage_badge(stage):
    c = STAGE_COLOR.get(stage, "#64748b")
    return f'<span class="stage-badge" style="background:{c}22;color:{c};border:1px solid {c}44">{stage}</span>'

def tone_chip(stage):
    c = STAGE_COLOR.get(stage, "#64748b")
    tone = STAGE_TONE.get(stage, stage)
    return f'<span class="tone-chip" style="background:{c}18;color:{c}">{tone}</span>'

@st.cache_data(ttl=30)
def load_invoices():
    try:
        return parse_csv_file(str(DEFAULT_CSV))
    except Exception as e:
        st.error(f"Could not load invoices: {e}")
        return []

def get_stats(records):
    total    = len(records)
    overdue  = sum(1 for r in records if r["days_overdue"] > 0)
    escalated= sum(1 for r in records if r["stage"] == "Escalated")
    sent_today = get_sent_today_count()
    return total, overdue, escalated, sent_today


# ── Sidebar ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="brand-header">
      <div class="brand-icon">⚡</div>
      <div>
        <div class="brand-title">CreditFlow</div>
        <div class="brand-sub">COLLECTIONS AGENT</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**Navigation**")
    page = st.radio(
        "", ["📊 Dashboard", "📋 Invoice Queue", "🕐 Audit Log", "📁 Upload Data"],
        label_visibility="collapsed"
    )

    st.divider()
    st.markdown("**Settings**")
    dry_run = st.toggle("Dry Run Mode", value=True, help="When ON, emails are simulated — not actually sent.")
    st.caption("🟡 ON = Simulate only  |  🟢 OFF = Real dispatch")

    st.divider()
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.markdown(
        f'<div class="stat-delta">CreditFlow v1.0.0<br>'
        f'{datetime.now().strftime("%d %b %Y · %H:%M")}</div>',
        unsafe_allow_html=True
    )


# ── Load data ────────────────────────────────────────────────────
records = load_invoices()
total, overdue, escalated, sent_today = get_stats(records)
df = pd.DataFrame(records) if records else pd.DataFrame()


# ════════════════════════════════════════════════════════════════
# PAGE 1 — DASHBOARD
# ════════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    st.markdown("## 📊 Dashboard")
    st.caption("Real-time overview of outstanding credit and follow-up activity")

    # ── Stat metrics ──────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Invoices",   total,       delta="Active receivables")
    c2.metric("Overdue Count",    overdue,     delta="Past due date",     delta_color="inverse")
    c3.metric("Emails Sent Today",sent_today,  delta="Non dry-run dispatches")
    c4.metric("Escalated to Legal",escalated,  delta="Pending legal review", delta_color="inverse")

    st.divider()

    # ── Chart ─────────────────────────────────────────────────
    col_chart, col_table = st.columns([1.4, 1])

    with col_chart:
        st.markdown("#### Overdue Distribution by Stage")
        if not df.empty:
            stages = ["Stage 1","Stage 2","Stage 3","Stage 4","Escalated"]
            colors = ["#4ade80","#facc15","#fb923c","#f87171","#c084fc"]
            counts = [len(df[df["stage"]==s]) for s in stages]

            fig = go.Figure(go.Bar(
                x=stages, y=counts,
                marker_color=colors,
                marker_line_width=0,
                text=counts,
                textposition="outside",
                textfont=dict(family="JetBrains Mono", size=12, color="#94a3b8"),
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="JetBrains Mono", color="#64748b", size=11),
                xaxis=dict(showgrid=False, showline=False, tickfont=dict(color="#8b9ab7")),
                yaxis=dict(showgrid=True, gridcolor="rgba(139,154,183,0.08)", showline=False, tickfont=dict(color="#8b9ab7")),
                margin=dict(l=0, r=0, t=20, b=0),
                height=280,
                bargap=0.35,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No invoice data loaded yet.")

    with col_table:
        st.markdown("#### Stage Summary")
        if not df.empty:
            summary_rows = []
            for s, c in zip(
                ["Stage 1","Stage 2","Stage 3","Stage 4","Escalated","Current"],
                ["#4ade80","#facc15","#fb923c","#f87171","#c084fc","#60a5fa"]
            ):
                cnt = len(df[df["stage"]==s])
                total_amt = df[df["stage"]==s]["amount_due"].sum()
                summary_rows.append({"Stage": s, "Count": cnt, "Total Due": fmt_inr(total_amt)})
            st.dataframe(
                pd.DataFrame(summary_rows),
                hide_index=True,
                use_container_width=True,
                height=240,
            )

    st.divider()
    st.markdown("#### Recent Invoices (Top 5 Most Overdue)")
    if not df.empty:
        top5 = df.sort_values("days_overdue", ascending=False).head(5)
        display = top5[["invoice_no","customer_name","amount_due","days_overdue","stage"]].copy()
        display.columns = ["Invoice No.", "Client", "Amount Due (₹)", "Days Overdue", "Stage"]
        display["Amount Due (₹)"] = display["Amount Due (₹)"].apply(lambda x: fmt_inr(x))
        st.dataframe(display, hide_index=True, use_container_width=True)


# ════════════════════════════════════════════════════════════════
# PAGE 2 — INVOICE QUEUE
# ════════════════════════════════════════════════════════════════
elif page == "📋 Invoice Queue":
    st.markdown("## 📋 Invoice Queue")
    st.caption("Select an invoice to generate and dispatch AI follow-up emails")

    if df.empty:
        st.warning("No invoices loaded. Upload a CSV or check data/invoices.csv.")
        st.stop()

    # ── Filters ───────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns([2, 1, 1])
    with fc1:
        search = st.text_input("🔍 Search invoice or client", placeholder="INV-2024-001 or Rajesh...")
    with fc2:
        stage_filter = st.selectbox("Stage", ["All Stages","Stage 1","Stage 2","Stage 3","Stage 4","Escalated","Current"])
    with fc3:
        sort_by = st.selectbox("Sort by", ["Days Overdue ↓","Amount ↓","Due Date ↑"])

    # Apply filters
    filtered = df.copy()
    if search:
        mask = (
            filtered["invoice_no"].str.contains(search, case=False, na=False) |
            filtered["customer_name"].str.contains(search, case=False, na=False)
        )
        filtered = filtered[mask]
    if stage_filter != "All Stages":
        filtered = filtered[filtered["stage"] == stage_filter]
    if sort_by == "Days Overdue ↓":
        filtered = filtered.sort_values("days_overdue", ascending=False)
    elif sort_by == "Amount ↓":
        filtered = filtered.sort_values("amount_due", ascending=False)
    else:
        filtered = filtered.sort_values("due_date")

    st.caption(f"Showing **{len(filtered)}** of {len(df)} invoices")

    # ── Table + row selection ─────────────────────────────────
    display_df = filtered[[
        "invoice_no", "customer_name", "customer_email",
        "amount_due", "due_date", "days_overdue", "stage"
    ]].copy()
    display_df.columns = ["Invoice No.", "Client", "Email", "Amount (₹)", "Due Date", "Days Overdue", "Stage"]
    display_df["Amount (₹)"] = display_df["Amount (₹)"].apply(fmt_inr)

    selected = st.dataframe(
        display_df,
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        height=320,
    )

    # ── Email generation panel ────────────────────────────────
    sel_rows = selected.selection.rows if selected.selection else []

    if sel_rows:
        inv_idx = filtered.iloc[sel_rows[0]]
        invoice = inv_idx.to_dict()
        stage   = invoice["stage"]
        color   = STAGE_COLOR.get(stage, "#fbbf24")

        st.divider()
        st.markdown(f"### ⚡ Email Agent — `{invoice['invoice_no']}`")

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Client",       invoice["customer_name"])
        mc2.metric("Amount Due",   fmt_inr(invoice["amount_due"]))
        mc3.metric("Days Overdue", f"{invoice['days_overdue']}d")
        mc4.metric("Stage",        stage)

        st.markdown(
            f'<div style="margin:0.5rem 0">Escalation tone: {tone_chip(stage)}</div>',
            unsafe_allow_html=True
        )

        # ── Blocked (Escalated) ──────────────────────────────
        if stage == "Escalated":
            st.markdown("""
            <div class="blocked-banner">
            🚨 <strong>Automation Blocked</strong> — This invoice is 30+ days overdue.
            Refer to the Legal / Finance Manager for manual review. No automated email will be sent.
            </div>
            """, unsafe_allow_html=True)

        elif stage == "Current":
            st.info("✅ This invoice is not yet overdue. No follow-up email needed.")

        else:
            # Generate button
            gen_key = f"email_{invoice['invoice_no']}"
            if st.button("⚡ Generate AI Email", key="gen_btn", type="primary", use_container_width=False):
                with st.spinner("Calling Gemini to draft email…"):
                    try:
                        result = generate_email(invoice)
                        st.session_state[gen_key] = result
                        st.success("Email generated successfully!")
                    except Exception as e:
                        st.error(f"Generation failed: {e}")

            # Show email if generated
            if gen_key in st.session_state:
                email_data = st.session_state[gen_key]

                st.markdown('<div class="section-title">Generated Email Preview</div>', unsafe_allow_html=True)
                st.markdown(f"""
                <div class="email-box">
                  <div class="section-title">SUBJECT</div>
                  <div class="email-subject">{email_data['subject']}</div>
                  <div class="section-title" style="margin-top:0.75rem">BODY</div>
                  <div class="email-body">{email_data['body']}</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("---")
                ba1, ba2, ba3 = st.columns([1, 1, 2])

                with ba1:
                    if st.button("🧪 Dry Run", use_container_width=True):
                        with st.spinner("Simulating send…"):
                            status = send_email(
                                to_email=invoice["customer_email"],
                                subject=email_data["subject"],
                                body=email_data["body"],
                                dry_run=True,
                            )
                            audit_id = log_action(
                                invoice_no=invoice["invoice_no"],
                                amount_due=invoice["amount_due"],
                                stage=stage,
                                tone=STAGE_TONE.get(stage, "Professional"),
                                send_status=status,
                                dry_run=True,
                            )
                            st.info(f"✅ Dry run logged — Audit ID: {audit_id}")
                            load_invoices.clear()

                with ba2:
                    if st.button("📤 Send Email", use_container_width=True, type="primary"):
                        if dry_run:
                            st.warning("Dry Run Mode is ON in sidebar — switching to dry_run=True.")
                            dr = True
                        else:
                            dr = False
                        with st.spinner("Dispatching…"):
                            status = send_email(
                                to_email=invoice["customer_email"],
                                subject=email_data["subject"],
                                body=email_data["body"],
                                dry_run=dr,
                            )
                            audit_id = log_action(
                                invoice_no=invoice["invoice_no"],
                                amount_due=invoice["amount_due"],
                                stage=stage,
                                tone=STAGE_TONE.get(stage, "Professional"),
                                send_status=status,
                                dry_run=dr,
                            )
                            st.success(f"✅ Email `{status}` — Audit ID: `{audit_id}`")
                            load_invoices.clear()

                with ba3:
                    if st.button("🔄 Regenerate", use_container_width=False):
                        if gen_key in st.session_state:
                            del st.session_state[gen_key]
                        st.rerun()
    else:
        st.info("👆 Click a row to open the Email Agent panel for that invoice.")


# ════════════════════════════════════════════════════════════════
# PAGE 3 — AUDIT LOG
# ════════════════════════════════════════════════════════════════
elif page == "🕐 Audit Log":
    st.markdown("## 🕐 Audit Log")
    st.caption("Chronological record of every email dispatch event")

    logs = get_all_logs()

    if not logs:
        st.info("No audit entries yet. Generate and send/dry-run an email to create entries.")
        st.stop()

    log_df = pd.DataFrame(logs)
    log_df["dry_run_label"] = log_df["dry_run"].apply(lambda x: "Yes" if x else "No")

    # Filters
    al1, al2 = st.columns([2, 1])
    with al1:
        log_search = st.text_input("🔍 Search invoice number", key="log_search")
    with al2:
        status_filter = st.selectbox("Send Status", ["All", "sent", "dry_run", "blocked_escalated"], key="log_status")

    filtered_logs = log_df.copy()
    if log_search:
        filtered_logs = filtered_logs[filtered_logs["invoice_no"].str.contains(log_search, case=False, na=False)]
    if status_filter != "All":
        filtered_logs = filtered_logs[filtered_logs["send_status"] == status_filter]

    st.caption(f"**{len(filtered_logs)}** entries found")

    display_log = filtered_logs[[
        "id", "timestamp", "invoice_no", "amount_due", "stage", "tone", "send_status", "dry_run_label"
    ]].copy()
    display_log.columns = ["ID", "Timestamp", "Invoice No.", "Amount (₹)", "Stage", "Tone", "Send Status", "Dry Run"]
    display_log["Amount (₹)"] = display_log["Amount (₹)"].apply(fmt_inr)

    st.dataframe(display_log, hide_index=True, use_container_width=True, height=480)

    st.divider()
    col_export, _ = st.columns([1, 3])
    with col_export:
        csv_bytes = display_log.to_csv(index=False).encode()
        st.download_button(
            "⬇️ Export Audit Log (CSV)",
            data=csv_bytes,
            file_name=f"audit_log_{date.today()}.csv",
            mime="text/csv",
            use_container_width=True,
        )


# ════════════════════════════════════════════════════════════════
# PAGE 4 — UPLOAD DATA
# ════════════════════════════════════════════════════════════════
elif page == "📁 Upload Data":
    st.markdown("## 📁 Upload Invoice Data")
    st.caption("Import invoice records from CSV or Excel for AI processing")

    st.markdown("""
    **Required columns:** `invoice_no`, `customer_name`, `customer_email`, `amount_due`, `due_date`

    **Supported formats:** `.csv`, `.xlsx`, `.xls`
    """)

    sample_csv = """invoice_no,customer_name,customer_email,amount_due,due_date
INV-2024-011,Kumar Logistics,kumar@example.com,55000,2025-04-10
INV-2024-012,Patel Corp,accounts@patel.in,135000,2025-04-15"""

    st.download_button(
        "⬇️ Download Sample CSV Template",
        data=sample_csv.encode(),
        file_name="sample_invoices.csv",
        mime="text/csv",
    )

    st.divider()
    uploaded = st.file_uploader(
        "Drop your CSV / Excel file here",
        type=["csv", "xlsx", "xls"],
        label_visibility="visible",
    )

    if uploaded:
        raw = uploaded.read()
        try:
            parsed = parse_upload(raw, uploaded.name)
            parsed_df = pd.DataFrame(parsed)
            st.success(f"✅ Parsed **{len(parsed_df)}** records from `{uploaded.name}`")

            st.markdown("#### Preview (first 10 rows)")
            preview = parsed_df.copy()
            preview["amount_due"] = preview["amount_due"].apply(fmt_inr)
            st.dataframe(preview.head(10), hide_index=True, use_container_width=True)

            if st.button("✅ Confirm Import — Save as Default Dataset", type="primary"):
                ext = uploaded.name.rsplit(".", 1)[-1].lower()
                save_path = DATA_DIR / f"invoices.{ext}"
                DATA_DIR.mkdir(exist_ok=True)
                save_path.write_bytes(raw)
                load_invoices.clear()
                st.success(f"📁 Saved to `data/invoices.{ext}` — {len(parsed_df)} invoices now active.")
                st.balloons()
                st.rerun()
        except Exception as e:
            st.error(f"❌ Failed to parse file: {e}")
            st.caption("Make sure the file has the required columns: invoice_no, customer_name, customer_email, amount_due, due_date")
