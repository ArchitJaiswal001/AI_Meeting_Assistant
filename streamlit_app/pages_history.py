"""
Meeting History dashboard — rebuilt as a card list with status badges
and a simple search/filter, instead of a plain table.
"""
import streamlit as st
import api_client as api
from style import section_label, status_badge_html
from config import BACKEND_URL


def render():
    try:
        meetings = api.list_meetings()
    except Exception as e:
        st.error(f"Could not load history: {e}")
        return

    with st.container(border=True):
        col1, col2 = st.columns([3, 2])
        with col1:
            section_label("Meeting History")
            st.caption(f"{len(meetings)} meeting(s) processed")
        with col2:
            search = st.text_input("Search", placeholder="Search by filename...", label_visibility="collapsed")

    st.write("")

    if not meetings:
        st.info("No meetings yet — go to **New Meeting** to process your first one.")
        return

    if search:
        meetings = [m for m in meetings if search.lower() in m["filename"].lower()]
        if not meetings:
            st.info("No meetings match your search.")
            return

    for m in meetings:
        with st.container(border=True):
            col1, col2, col3 = st.columns([4, 2, 1])
            with col1:
                st.markdown(f"**{m['filename']}**")
                st.caption(m["created_at"][:19].replace("T", " "))
            with col2:
                st.markdown(status_badge_html(m["status"]), unsafe_allow_html=True)
            with col3:
                if st.button("Open →", key=f"open_{m['id']}", use_container_width=True):
                    _open_meeting(m["id"])


def _open_meeting(meeting_id: str):
    try:
        meeting = api.get_meeting(meeting_id)
        st.session_state.meeting_id = meeting_id
        st.session_state.meeting_data = meeting
        st.session_state.stage = "done"
        st.session_state.active_page = "New Meeting"
        st.rerun()
    except Exception as e:
        st.error(f"Could not open meeting: {e}")