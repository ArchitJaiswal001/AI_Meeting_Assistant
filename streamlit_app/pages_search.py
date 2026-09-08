"""
Phase 4: Search across ALL past meetings — a chat-style page where
questions are answered using whichever meetings are actually relevant,
with the source meetings shown so answers are traceable, not a black box.
"""
import streamlit as st
import api_client as api
from style import section_label


def render():
    with st.container(border=True):
        section_label("Search all meetings")
        st.caption("Ask a question spanning your whole meeting history, not just one meeting.")

        if "search_history" not in st.session_state:
            st.session_state.search_history = []

        for role, content in st.session_state.search_history:
            with st.chat_message(role):
                if isinstance(content, dict):
                    st.write(content["answer"])
                    if content["sources"]:
                        sources_str = ", ".join(s["filename"] for s in content["sources"])
                        st.caption(f"Sources: {sources_str}")
                else:
                    st.write(content)

        question = st.chat_input("e.g. When did we last discuss the pricing model?")
        if question:
            st.session_state.search_history.append(("user", question))
            with st.chat_message("user"):
                st.write(question)
            with st.chat_message("assistant"):
                with st.spinner("Searching your meetings..."):
                    try:
                        result = api.search_across_meetings(question)
                        st.write(result["answer"])
                        if result["sources"]:
                            sources_str = ", ".join(s["filename"] for s in result["sources"])
                            st.caption(f"Sources: {sources_str}")
                        st.session_state.search_history.append(("assistant", result))
                    except Exception as e:
                        st.error(f"Search failed: {e}")