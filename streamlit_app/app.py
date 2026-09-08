"""
Run with:
    streamlit run app.py

Entry point. Gates the whole app behind login. Now has 4 nav items:
New Meeting, History, Search, Analytics.
"""
import streamlit as st
from streamlit_option_menu import option_menu
import pages_new_meeting
import pages_history
import pages_auth
import pages_analytics
import pages_search
from style import inject_custom_css, render_header

st.set_page_config(
    page_title="AI Meeting Assistant",
    page_icon="🗓️",
    layout="centered",
    initial_sidebar_state="expanded",
)

inject_custom_css()

if not st.session_state.get("auth_token"):
    pages_auth.render()
    st.stop()

with st.sidebar:
    st.markdown(
        '<div style="font-size:18px; font-weight:700; padding: 4px 0 4px 0;">🗓️ Meeting AI</div>',
        unsafe_allow_html=True,
    )
    st.caption(f"Logged in as {st.session_state.get('user_email', '')}")

    nav_options = ["New Meeting", "History", "Search", "Analytics"]
    page = option_menu(
        menu_title=None,
        options=nav_options,
        icons=["mic", "clock-history", "search", "bar-chart"],
        default_index=nav_options.index(st.session_state.get("active_page", "New Meeting")),
        styles={
            "container": {"padding": "0", "background-color": "transparent"},
            "icon": {"color": "#8FA3D1", "font-size": "16px"},
            "nav-link": {
                "font-size": "14px",
                "text-align": "left",
                "margin": "2px 0",
                "border-radius": "8px",
                "color": "#E8EEFB",
            },
            "nav-link-selected": {"background-color": "#2E5EFF"},
        },
    )
    st.session_state.active_page = page

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    if st.button("Log out", use_container_width=True):
        for key in ["auth_token", "user_email", "meeting_id", "meeting_data", "stage"]:
            st.session_state.pop(key, None)
        st.rerun()

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    st.caption("Backend status")
    try:
        import requests
        requests.get("http://localhost:8000/", timeout=1)
        st.markdown("🟢 Connected — `localhost:8000`")
    except Exception:
        st.markdown("🔴 Not reachable — start the backend")

render_header()

if page == "New Meeting":
    pages_new_meeting.render()
elif page == "History":
    pages_history.render()
elif page == "Search":
    pages_search.render()
elif page == "Analytics":
    pages_analytics.render()