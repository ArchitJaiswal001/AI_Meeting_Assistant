"""
The main workflow page: upload or record audio -> process -> view/edit
results -> send email.

Includes meeting type selector, language selector, sentiment pill,
"Ask a question about this meeting" chat, RETRY on failure (reuses the
already-stored audio, no re-recording needed), action item completion
checkboxes, and a Notion sync button.
"""
import streamlit as st
import pandas as pd
import time
from audio_recorder_streamlit import audio_recorder
import api_client as api
from style import section_label, status_badge_html, stat_chip, sentiment_pill

MEETING_TYPES = ["General", "Standup", "Client Call", "Brainstorm"]
LANGUAGES = {
    "auto": "Auto-detect", "en": "English", "hi": "Hindi", "es": "Spanish",
    "fr": "French", "de": "German", "pt": "Portuguese", "ja": "Japanese", "zh": "Chinese",
}


def render():
    stage = st.session_state.get("stage", "idle")

    if st.session_state.get("meeting_id") and stage != "idle":
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("↺ Reset", use_container_width=True):
                for key in ["meeting_id", "meeting_data", "stage", "chat_history"]:
                    st.session_state.pop(key, None)
                st.rerun()

    if stage == "idle":
        _render_capture_stage()
    elif stage == "processing":
        _poll_until_done(st.session_state.meeting_id)
    elif stage == "done":
        _render_results(st.session_state.meeting_data)


def _render_capture_stage():
    with st.container(border=True):
        section_label("Start a new meeting")

        meeting_type = st.selectbox(
            "Meeting type",
            MEETING_TYPES,
            help="Changes what the AI focuses on — e.g. Standup emphasizes blockers, Client Call emphasizes commitments.",
        )
        language = st.selectbox(
            "Language",
            options=list(LANGUAGES.keys()),
            format_func=lambda code: LANGUAGES[code],
            help="Transcript and summary will be generated in this language. Auto-detect works well for most cases.",
        )

        tab1, tab2 = st.tabs(["📁  Upload a file", "🎙️  Record live"])

        with tab1:
            st.write("")
            uploaded = st.file_uploader(
                "Upload an audio or video file",
                type=["mp3", "wav", "m4a", "mp4", "webm"],
                label_visibility="collapsed",
            )
            st.write("")
            if uploaded is not None:
                st.caption(f"Selected: **{uploaded.name}** ({uploaded.size / (1024*1024):.1f} MB)")
                if st.button("Process uploaded file", type="primary", use_container_width=True):
                    _handle_audio(uploaded.read(), uploaded.name, meeting_type, language, is_recording=False)

        with tab2:
            st.write("")
            st.caption("Click the mic, speak, click again to stop.")
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                audio_bytes = audio_recorder(pause_threshold=120.0, icon_size="2x")
            if audio_bytes:
                st.audio(audio_bytes, format="audio/wav")
                if st.button("Process this recording", type="primary", use_container_width=True):
                    _handle_audio(audio_bytes, "live_recording.wav", meeting_type, language, is_recording=True)


def _handle_audio(audio_bytes: bytes, filename: str, meeting_type: str, language: str, is_recording: bool):
    with st.spinner("Uploading..."):
        try:
            response = (
                api.upload_recording(audio_bytes, meeting_type, language)
                if is_recording
                else api.upload_file(audio_bytes, filename, meeting_type, language)
            )
            meeting_id = response["meeting_id"]
            api.start_processing(meeting_id)
            st.session_state.meeting_id = meeting_id
            st.session_state.stage = "processing"
            st.rerun()
        except Exception as e:
            st.error(f"Upload failed: {e}")


STATUS_STEPS = {
    "queued": ("Queued for processing...", 10),
    "transcribing": ("Transcribing audio (Deepgram)...", 40),
    "summarizing": ("Summarizing + extracting action items (LLM)...", 75),
    "done": ("Done", 100),
}


def _poll_until_done(meeting_id: str):
    with st.container(border=True):
        section_label("Processing")
        progress_bar = st.progress(0)
        status_text = st.empty()

        while True:
            meeting = api.get_meeting(meeting_id)
            status = meeting.get("status", "queued")

            if status == "error":
                status_text.empty()
                progress_bar.empty()
                st.error(f"Processing failed: {meeting.get('summary', 'Unknown error')}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔁 Retry (uses the same recording)", type="primary", use_container_width=True):
                        try:
                            api.start_processing(meeting_id)
                            st.session_state.stage = "processing"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Retry failed: {e}")
                with col2:
                    if st.button("Start over with new audio", use_container_width=True):
                        for key in ["meeting_id", "meeting_data", "stage"]:
                            st.session_state.pop(key, None)
                        st.rerun()
                return

            if status == "done":
                progress_bar.progress(100)
                status_text.markdown("✅ **Done**")
                st.session_state.meeting_data = meeting
                st.session_state.stage = "done"
                time.sleep(0.4)
                st.rerun()
                return

            label, pct = STATUS_STEPS.get(status, ("Processing...", 20))
            progress_bar.progress(pct)
            status_text.text(label)
            time.sleep(1.5)


def _render_results(meeting: dict):
    meeting_id = meeting["id"]
    items = meeting.get("action_items") or []
    word_count = len((meeting.get("transcript") or "").split())

    with st.container(border=True):
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown(f"**{meeting.get('filename', 'Meeting')}**")
            badge_row = status_badge_html(meeting.get("status", "done"))
            st.markdown(badge_row, unsafe_allow_html=True)
            st.caption(f"Type: {meeting.get('meeting_type', 'General')}")
        with col2:
            c1, c2 = st.columns(2)
            with c1:
                done_count = sum(1 for i in items if i.get("done"))
                stat_chip(f"{done_count}/{len(items)}", "Items done")
            with c2:
                stat_chip(f"{word_count:,}", "Words")

    st.write("")

    with st.container(border=True):
        top_col1, top_col2 = st.columns([3, 2])
        with top_col1:
            section_label("Summary")
        with top_col2:
            sentiment_pill(meeting.get("sentiment", ""))
        st.write(meeting.get("summary", ""))

    st.write("")

    with st.container(border=True):
        section_label("Action items")
        st.caption("Check items off as done, edit any field, add/remove rows, then save.")

        df = pd.DataFrame(items) if items else pd.DataFrame(columns=["done", "task", "owner", "deadline"])
        if "done" not in df.columns:
            df["done"] = False
        df = df[["done", "task", "owner", "deadline"]]
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "done": st.column_config.CheckboxColumn("Done", width="small"),
                "task": st.column_config.TextColumn("Task", width="large"),
                "owner": st.column_config.TextColumn("Owner"),
                "deadline": st.column_config.TextColumn("Deadline"),
            },
            key=f"editor_{meeting_id}",
        )

        btn_col1, btn_col2 = st.columns([1, 1])
        with btn_col1:
            if st.button("💾  Save changes", use_container_width=True):
                updated_items = edited_df.fillna("").to_dict(orient="records")
                for it in updated_items:
                    it["done"] = bool(it.get("done", False))
                try:
                    updated = api.update_meeting(meeting_id, action_items=updated_items)
                    st.session_state.meeting_data = updated
                    st.toast("Saved", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save: {e}")
        with btn_col2:
            if st.button("📌  Sync to Notion", use_container_width=True):
                with st.spinner("Creating tasks in Notion..."):
                    try:
                        result = api.sync_to_notion(meeting_id)
                        if result["synced_count"]:
                            st.success(f"Synced {result['synced_count']} task(s) to Notion")
                        if result["failed_count"]:
                            st.warning(f"{result['failed_count']} item(s) failed to sync")
                    except Exception as e:
                        st.error(f"Notion sync failed: {e}")

    st.write("")

    with st.container(border=True):
        section_label("Ask a question about this meeting")
        st.caption("Answered using the full transcript as context.")

        chat_key = f"chat_history_{meeting_id}"
        if chat_key not in st.session_state:
            st.session_state[chat_key] = []

        for role, text in st.session_state[chat_key]:
            with st.chat_message(role):
                st.write(text)

        question = st.chat_input("e.g. What did Priya say about the deadline?")
        if question:
            st.session_state[chat_key].append(("user", question))
            with st.chat_message("user"):
                st.write(question)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        answer = api.ask_question(meeting_id, question)
                        st.write(answer)
                        st.session_state[chat_key].append(("assistant", answer))
                    except Exception as e:
                        st.error(f"Couldn't get an answer: {e}")

    st.write("")

    with st.container(border=True):
        section_label("Follow-up email")
        st.text_input("Subject", value=meeting.get("email_subject", ""), disabled=True, label_visibility="collapsed")
        st.code(meeting.get("email_body", ""), language=None)

        dl1, dl2, dl3 = st.columns(3)
        with dl1:
            st.download_button("⬇ Transcript", data=meeting.get("transcript", ""),
                                file_name=f"transcript_{meeting_id[:8]}.txt", use_container_width=True)
        with dl2:
            st.download_button("⬇ Summary", data=meeting.get("summary", ""),
                                file_name=f"summary_{meeting_id[:8]}.txt", use_container_width=True)
        with dl3:
            email_txt = f"Subject: {meeting.get('email_subject','')}\n\n{meeting.get('email_body','')}"
            st.download_button("⬇ Email", data=email_txt,
                                file_name=f"email_{meeting_id[:8]}.txt", use_container_width=True)

        st.write("")
        recipients_input = st.text_input(
            "Recipient email(s)", placeholder="name1@email.com, name2@email.com"
        )
        if st.button("📤  Send email", type="primary"):
            recipients = [r.strip() for r in recipients_input.split(",") if r.strip()]
            if not recipients:
                st.warning("Enter at least one recipient email")
            else:
                try:
                    api.send_followup_email(meeting_id, recipients)
                    st.success(f"Email sent to: {', '.join(recipients)}")
                except Exception as e:
                    st.error(f"Failed to send: {e}")

    with st.expander("View full transcript"):
        st.text(meeting.get("transcript", ""))