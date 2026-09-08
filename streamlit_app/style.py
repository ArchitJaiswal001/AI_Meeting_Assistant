"""
Shared styling + small reusable UI components, imported by every page
so the app looks consistent instead of each page inventing its own look.
"""
import streamlit as st

NAVY = "#0B1A3D"
BLUE = "#2E5EFF"
CYAN = "#06B6D4"
GREY = "#5B6B8C"
BORDER = "#D7E3FA"
CARD_BG = "#FFFFFF"

STATUS_STYLES = {
    "queued":       ("#8592AD", "Queued"),
    "transcribing": ("#F59E0B", "Transcribing"),
    "summarizing":  ("#F59E0B", "Summarizing"),
    "done":         ("#16A34A", "Ready"),
    "email_sent":   ("#2E5EFF", "Email sent"),
    "error":        ("#DC2626", "Failed"),
    "uploaded":     ("#8592AD", "Uploaded"),
}


def inject_custom_css():
    st.markdown(f"""
    <style>
        /* ---- Global spacing & font ---- */
        .block-container {{
            padding-top: 1.5rem;
            padding-bottom: 3rem;
            max-width: 900px;
        }}
        html, body, [class*="css"] {{
            font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
        }}

        /* ---- Hide default Streamlit chrome for a cleaner, branded look ---- */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header[data-testid="stHeader"] {{background: transparent;}}

        /* ---- Sidebar ---- */
        section[data-testid="stSidebar"] {{
            background-color: {NAVY};
        }}
        section[data-testid="stSidebar"] * {{
            color: #E8EEFB !important;
        }}
        section[data-testid="stSidebar"] .stCaption {{
            color: #8FA3D1 !important;
        }}

        /* ---- Cards (used via st.container(border=True)) ---- */
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: 14px !important;
            border-color: {BORDER} !important;
            background-color: {CARD_BG};
            box-shadow: 0 2px 10px rgba(11, 26, 61, 0.06);
        }}

        /* ---- Buttons ---- */
        .stButton > button {{
            border-radius: 8px;
            font-weight: 500;
            transition: transform 0.05s ease;
        }}
        .stButton > button:active {{
            transform: scale(0.98);
        }}
        .stButton > button[kind="primary"] {{
            background-color: {BLUE};
            border: none;
        }}

        /* ---- Tabs ---- */
        button[data-baseweb="tab"] {{
            font-weight: 500;
        }}

        /* ---- Section headers inside cards ---- */
        .section-label {{
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: {GREY};
            margin-bottom: 6px;
        }}

        /* ---- Status badge ---- */
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            font-weight: 600;
            padding: 4px 12px;
            border-radius: 999px;
        }}

        /* ---- Metric-style stat chip ---- */
        .stat-chip {{
            background: #EEF3FF;
            border-radius: 10px;
            padding: 10px 14px;
            text-align: center;
        }}
        .stat-chip .stat-value {{
            font-size: 22px;
            font-weight: 700;
            color: {NAVY};
        }}
        .stat-chip .stat-label {{
            font-size: 11px;
            color: {GREY};
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}

        /* ---- Responsiveness: tighten padding on narrow/mobile screens ---- */
        @media (max-width: 640px) {{
            .block-container {{
                padding-left: 1rem;
                padding-right: 1rem;
            }}
        }}
    </style>
    """, unsafe_allow_html=True)


def render_header():
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:4px;">
        <span style="font-size:30px;">🗓️</span>
        <div>
            <div style="font-size:24px; font-weight:700; color:{NAVY}; line-height:1.1;">
                AI Meeting Assistant
            </div>
            <div style="font-size:13px; color:{GREY};">
                Record or upload → get a summary, action items, and a follow-up email.
            </div>
        </div>
    </div>
    <hr style="margin: 14px 0 20px 0; border: none; border-top: 1px solid {BORDER};">
    """, unsafe_allow_html=True)


def status_badge_html(status: str) -> str:
    color, label = STATUS_STYLES.get(status, ("#8592AD", status.title()))
    return (
        f'<span class="status-badge" style="background:{color}22; color:{color};">'
        f'<span style="width:6px;height:6px;border-radius:50%;background:{color};"></span>'
        f'{label}</span>'
    )


def section_label(text: str):
    st.markdown(f'<div class="section-label">{text}</div>', unsafe_allow_html=True)


def stat_chip(value, label: str):
    st.markdown(f"""
    <div class="stat-chip">
        <div class="stat-value">{value}</div>
        <div class="stat-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def sentiment_pill(sentiment: str):
    """Phase 2: small pill showing the detected meeting tone."""
    if not sentiment:
        return
    st.markdown(f"""
    <span style="display:inline-flex; align-items:center; gap:6px; font-size:12px;
                 color:{GREY}; background:#F1F4FA; padding:4px 12px; border-radius:999px;">
        🎭 {sentiment}
    </span>
    """, unsafe_allow_html=True)