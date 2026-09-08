"""
Every call to the FastAPI backend lives here.

All requests attach the logged-in user's token via
_auth_headers(), read from Streamlit's session state.
"""

import requests
import streamlit as st
from config import BACKEND_URL


# FastAPI backend URL
API_BASE = BACKEND_URL.rstrip("/")


def _auth_headers() -> dict:
    token = st.session_state.get("auth_token")

    if not token:
        raise RuntimeError("Not logged in")

    return {
        "Authorization": f"Bearer {token}"
    }


# ---------------- Auth ----------------

def register(email: str, password: str) -> dict:
    res = requests.post(
        f"{API_BASE}/api/auth/register",
        json={
            "email": email,
            "password": password
        }
    )

    if not res.ok:
        raise RuntimeError(
            res.json().get("detail", "Registration failed")
        )

    return res.json()


def login(email: str, password: str) -> dict:
    res = requests.post(
        f"{API_BASE}/api/auth/login",
        json={
            "email": email,
            "password": password
        }
    )

    if not res.ok:
        raise RuntimeError(
            res.json().get("detail", "Login failed")
        )

    return res.json()


# ---------------- Meetings ----------------

def upload_file(
    file_bytes: bytes,
    filename: str,
    meeting_type: str = "General",
    language: str = "auto"
) -> dict:

    files = {
        "file": (filename, file_bytes)
    }

    data = {
        "meeting_type": meeting_type,
        "language": language
    }

    res = requests.post(
        f"{API_BASE}/api/upload",
        files=files,
        data=data,
        headers=_auth_headers()
    )

    res.raise_for_status()

    return res.json()


def upload_recording(
    audio_bytes: bytes,
    meeting_type: str = "General",
    language: str = "auto"
) -> dict:

    files = {
        "file": (
            "recording.wav",
            audio_bytes,
            "audio/wav"
        )
    }

    data = {
        "meeting_type": meeting_type,
        "language": language
    }

    res = requests.post(
        f"{API_BASE}/api/record",
        files=files,
        data=data,
        headers=_auth_headers()
    )

    res.raise_for_status()

    return res.json()


def start_processing(meeting_id: str) -> dict:

    res = requests.post(
        f"{API_BASE}/api/process/{meeting_id}",
        headers=_auth_headers(),
        timeout=10
    )

    if not res.ok:
        raise RuntimeError(
            res.json().get(
                "detail",
                "Failed to start processing"
            )
        )

    return res.json()


def get_meeting(meeting_id: str) -> dict:

    res = requests.get(
        f"{API_BASE}/api/meeting/{meeting_id}",
        headers=_auth_headers()
    )

    res.raise_for_status()

    return res.json()


def update_meeting(
    meeting_id: str,
    action_items=None,
    email_subject=None,
    email_body=None
) -> dict:

    payload = {}

    if action_items is not None:
        payload["action_items"] = action_items

    if email_subject is not None:
        payload["email_subject"] = email_subject

    if email_body is not None:
        payload["email_body"] = email_body

    res = requests.patch(
        f"{API_BASE}/api/meeting/{meeting_id}",
        json=payload,
        headers=_auth_headers()
    )

    res.raise_for_status()

    return res.json()


def list_meetings() -> list:

    res = requests.get(
        f"{API_BASE}/api/meetings",
        headers=_auth_headers()
    )

    res.raise_for_status()

    return res.json()


def send_followup_email(
    meeting_id: str,
    recipients: list
) -> dict:

    res = requests.post(
        f"{API_BASE}/api/send-email/{meeting_id}",
        json={
            "recipients": recipients
        },
        headers=_auth_headers()
    )

    if not res.ok:
        raise RuntimeError(
            res.json().get(
                "detail",
                "Sending email failed"
            )
        )

    return res.json()


def ask_question(
    meeting_id: str,
    question: str
) -> str:

    res = requests.post(
        f"{API_BASE}/api/chat/{meeting_id}",
        json={
            "question": question
        },
        headers=_auth_headers(),
        timeout=60
    )

    if not res.ok:
        raise RuntimeError(
            res.json().get(
                "detail",
                "Failed to get an answer"
            )
        )

    return res.json()["answer"]


# ---------------- Phase 4 ----------------

def sync_to_notion(meeting_id: str) -> dict:

    res = requests.post(
        f"{API_BASE}/api/notion/sync/{meeting_id}",
        headers=_auth_headers(),
        timeout=60
    )

    if not res.ok:
        raise RuntimeError(
            res.json().get(
                "detail",
                "Notion sync failed"
            )
        )

    return res.json()


def get_analytics() -> dict:

    res = requests.get(
        f"{API_BASE}/api/analytics",
        headers=_auth_headers()
    )

    res.raise_for_status()

    return res.json()


def search_across_meetings(
    question: str
) -> dict:

    res = requests.post(
        f"{API_BASE}/api/search",
        json={
            "question": question
        },
        headers=_auth_headers(),
        timeout=60
    )

    if not res.ok:
        raise RuntimeError(
            res.json().get(
                "detail",
                "Search failed"
            )
        )

    return res.json()