"""
helpers.py — Utility functions: CSV export, chart data prep, shared CSS.
"""

import pandas as pd
import io
import streamlit as st
from datetime import datetime


def records_to_df(records: list) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    # Friendly column names
    rename = {
        "employee_id": "ID",
        "name": "Name",
        "department": "Department",
        "role": "Role",
        "date": "Date",
        "check_in": "Check-In",
        "check_out": "Check-Out",
        "status": "Status",
        "method": "Method",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    for col in ["Check-In", "Check-Out"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%H:%M:%S")
    return df


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


def format_duration(check_in_str, check_out_str) -> str:
    try:
        ci = datetime.fromisoformat(str(check_in_str))
        co = datetime.fromisoformat(str(check_out_str))
        delta = co - ci
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m = rem // 60
        return f"{h}h {m}m"
    except Exception:
        return "—"


# ── Shared CSS injector ───────────────────────────────────────────────────────

SHARED_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* Premium Typography for core elements only */
    h1, h2, h3, h4, h5, h6, p, label {
        font-family: 'Inter', sans-serif;
    }

    /* ── Base ── */
    .stApp {
        background: linear-gradient(135deg, #0d0f1a 0%, #111827 50%, #0a0d1a 100%);
        min-height: 100vh;
    }

    /* ── Cards ── */
    .glass-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 20px;
        padding: 24px;
        backdrop-filter: blur(16px);
        box-shadow: 0 4px 24px -1px rgba(0, 0, 0, 0.2);
        margin-bottom: 20px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .glass-card:hover {
        transform: translateY(-4px);
        background: rgba(255,255,255,0.05);
        border-color: rgba(108,99,255,0.4);
        box-shadow: 0 12px 40px rgba(108,99,255,0.12);
    }

    /* ── Metric cards ── */
    .metric-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 18px;
        padding: 24px;
        text-align: center;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .metric-card::before {
        content: "";
        position: absolute;
        top: 0; left: 0; width: 4px; height: 100%;
        background: linear-gradient(to bottom, #6c63ff, #3ecfcf);
        opacity: 0.8;
    }
    .metric-card:hover {
        background: rgba(255,255,255,0.06);
        border-color: rgba(108,99,255,0.3);
        transform: scale(1.02);
    }
    .metric-value {
        font-size: 2.6rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 0%, #a9a4ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.2;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #9ca3af;
        margin-top: 8px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    .metric-icon {
        font-size: 1.5rem;
        margin-bottom: 12px;
        opacity: 0.9;
    }

    /* ── User Card Grid ── */
    .user-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 20px;
        padding: 10px 0;
    }
    .user-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 16px;
        padding: 20px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        transition: all 0.3s ease;
    }
    .user-card:hover {
        background: rgba(255,255,255,0.05);
        border-color: rgba(108,99,255,0.3);
    }
    .user-card-header {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .user-card-content {
        font-size: 0.85rem;
        color: #9ca3af;
        line-height: 1.6;
    }

    /* ── Section headers ── */
    .section-title {
        font-size: 1.6rem;
        font-weight: 800;
        color: #f8fafc;
        margin-bottom: 8px;
        letter-spacing: -0.02em;
    }
    .section-subtitle {
        font-size: 0.95rem;
        color: #94a3b8;
        margin-bottom: 28px;
    }

    /* ── Badge ── */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 12px;
        border-radius: 8px;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-green  { background: rgba(34, 197, 94, 0.1); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.2); }
    .badge-red    { background: rgba(239, 68, 68, 0.1); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.2); }
    .badge-purple { background: rgba(99, 102, 241, 0.1); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.2); }
    .badge-teal   { background: rgba(20, 184, 166, 0.1); color: #2dd4bf; border: 1px solid rgba(20, 184, 166, 0.2); }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background-color: #0a0d17 !important;
        background-image: 
            radial-gradient(at 0% 0%, rgba(108,99,255,0.05) 0px, transparent 50%),
            radial-gradient(at 100% 0%, rgba(62,207,207,0.05) 0px, transparent 50%) !important;
        border-right: 1px solid rgba(255,255,255,0.05) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #94a3b8 !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        letter-spacing: 0.01em;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        padding: 0.6rem 1.6rem !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
    }
    .stButton > button:hover {
        opacity: 0.95 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 20px rgba(99, 102, 241, 0.3) !important;
    }
    .stButton > button:active {
        transform: translateY(0) !important;
    }

    /* Secondary/Delete Button Styling */
    div.stButton > button:has(span:contains("Delete")),
    div.stButton > button:has(span:contains("🗑️")) {
        background: rgba(239, 68, 68, 0.1) !important;
        color: #f87171 !important;
        border: 1px solid rgba(239, 68, 68, 0.2) !important;
        box-shadow: none !important;
    }
    div.stButton > button:has(span:contains("Delete")):hover,
    div.stButton > button:has(span:contains("🗑️")):hover {
        background: rgba(239, 68, 68, 0.2) !important;
        border-color: rgba(239, 68, 68, 0.4) !important;
    }

    /* ── Inputs ── */
    .stTextInput > div > div, .stSelectbox > div > div, .stDateInput > div > div {
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px !important;
        transition: border-color 0.2s ease !important;
    }
    .stTextInput > div > div:focus-within {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 1px #6366f1 !important;
    }

    /* ── Divider ── */
    .gradient-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(108,99,255,0.4), rgba(62,207,207,0.4), transparent);
        margin: 28px 0;
    }

    /* ── Alert boxes ── */
    .success-box, .error-box, .info-box {
        border-radius: 14px;
        padding: 16px 20px;
        font-size: 0.9rem;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .success-box { background: rgba(34, 197, 94, 0.1); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.2); }
    .error-box   { background: rgba(239, 68, 68, 0.1); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.2); }
    .info-box    { background: rgba(99, 102, 241, 0.1); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.2); }

    /* Hide Streamlit elements */
    #MainMenu, footer, header, .stDeployButton { visibility: hidden; }
</style>
</style>
"""


def inject_css():
    st.markdown(SHARED_CSS, unsafe_allow_html=True)
