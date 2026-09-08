"""
Main FastAPI app. Run with:
    uvicorn main:app --reload

Routes:
  POST  /api/auth/register       -> create an account
  POST  /api/auth/login          -> log in, get a JWT token
  POST  /api/upload              -> upload an audio/video file (auth required)
  POST  /api/record               -> upload a browser-recorded audio blob (auth required)
  POST  /api/process/{id}         -> kicks off processing (also used to RETRY on the same file)
  GET   /api/meeting/{id}         -> fetch a meeting's current status/results
  PATCH /api/meeting/{id}         -> update action items (incl. done flag) / email draft
  GET   /api/meetings             -> list the logged-in user's past meetings
  POST  /api/send-email/{id}      -> send the follow-up email
  POST  /api/chat/{id}            -> ask a question about ONE meeting
  POST  /api/notion/sync/{id}     -> Phase 4: sync action items to Notion as tasks
  GET   /api/analytics            -> Phase 4: aggregate stats dashboard
  POST  /api/search               -> Phase 4: ask a question across ALL meetings
"""
import uuid
import os
import json
import time
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware

from config import UPLOAD_DIR, ALLOWED_ORIGINS
from database import (
    init_db, create_meeting, update_meeting, get_meeting, list_meetings,
    list_meetings_with_content, get_analytics, create_user, get_user_by_email,
)
from models import (
    MeetingResult, SendEmailRequest, UpdateMeetingRequest, ChatRequest, ChatResponse,
    RegisterRequest, LoginRequest, TokenResponse,
    NotionSyncResponse, SearchRequest, SearchResponse, AnalyticsResponse,
)
from auth import hash_password, verify_password, create_access_token, get_current_user_id
from services.transcription import transcribe_audio
from services.summarizer import summarize_transcript, answer_question
from services.emailer import send_email
from services.audio_utils import compress_audio_for_transcription
from services.notion_service import sync_action_items_to_notion
from services.search_service import search_and_answer

app = FastAPI(title="AI Meeting Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS.split(",") if ALLOWED_ORIGINS != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


def _save_upload(file: UploadFile, meeting_id: str) -> str:
    extension = os.path.splitext(file.filename)[1] or ".webm"
    file_path = os.path.join(UPLOAD_DIR, f"{meeting_id}{extension}")
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    return file_path


def _require_ownership(meeting: dict, user_id: str):
    if meeting is None or meeting.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Meeting not found")


# ---------------- Auth ----------------

@app.post("/api/auth/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    if get_user_by_email(request.email):
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user_id = create_user(request.email, hash_password(request.password))
    token = create_access_token(user_id, request.email)
    return {"access_token": token, "email": request.email}


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = get_user_by_email(request.email)
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token(user["id"], user["email"])
    return {"access_token": token, "email": user["email"]}


# ---------------- Meetings ----------------

@app.post("/api/upload")
async def upload_meeting(
    file: UploadFile = File(...),
    meeting_type: str = Form("General"),
    language: str = Form("auto"),
    user_id: str = Depends(get_current_user_id),
):
    meeting_id = str(uuid.uuid4())
    file_path = _save_upload(file, meeting_id)
    create_meeting(meeting_id, filename=file.filename, user_id=user_id, meeting_type=meeting_type, language=language)
    update_meeting(meeting_id, status="uploaded")
    return {"meeting_id": meeting_id, "file_path": file_path}


@app.post("/api/record")
async def record_meeting(
    file: UploadFile = File(...),
    meeting_type: str = Form("General"),
    language: str = Form("auto"),
    user_id: str = Depends(get_current_user_id),
):
    meeting_id = str(uuid.uuid4())
    file_path = _save_upload(file, meeting_id)
    create_meeting(
        meeting_id,
        filename="live_recording" + os.path.splitext(file_path)[1],
        user_id=user_id,
        meeting_type=meeting_type,
        language=language,
    )
    update_meeting(meeting_id, status="uploaded")
    return {"meeting_id": meeting_id, "file_path": file_path}


async def _run_pipeline(meeting_id: str, file_path: str, meeting_type: str, language: str):
    pipeline_start = time.perf_counter()
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"[{meeting_id[:8]}] Starting pipeline — {file_size_mb:.2f} MB, type: {meeting_type}, lang: {language}")

    try:
        update_meeting(meeting_id, status="transcribing")

        t0 = time.perf_counter()
        audio_path_to_use = compress_audio_for_transcription(file_path)
        print(f"[{meeting_id[:8]}] Compression took {time.perf_counter() - t0:.2f}s")

        t0 = time.perf_counter()
        transcript = await transcribe_audio(audio_path_to_use, language=language)
        print(f"[{meeting_id[:8]}] Transcription took {time.perf_counter() - t0:.2f}s")

        update_meeting(meeting_id, transcript=transcript, status="summarizing")
        t0 = time.perf_counter()
        result = await summarize_transcript(transcript, meeting_type=meeting_type, language=language)
        print(f"[{meeting_id[:8]}] Summarization took {time.perf_counter() - t0:.2f}s")

        update_meeting(
            meeting_id,
            status="done",
            summary=result["summary"],
            sentiment=result.get("sentiment", ""),
            action_items=json.dumps(result["action_items"]),
            email_subject=result["email_subject"],
            email_body=result["email_body"],
        )
        print(f"[{meeting_id[:8]}] TOTAL pipeline time: {time.perf_counter() - pipeline_start:.2f}s")
    except Exception as e:
        update_meeting(meeting_id, status="error", summary=str(e))
        print(f"[{meeting_id[:8]}] FAILED after {time.perf_counter() - pipeline_start:.2f}s: {e}")


@app.post("/api/process/{meeting_id}")
async def process_meeting(meeting_id: str, background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user_id)):
    """
    Kicks off the pipeline for a meeting whose audio file is already on
    disk. This same endpoint is used both for a fresh upload AND for a
    RETRY after a failure — since the audio was saved under meeting_id
    at upload time, retrying never needs the file re-sent. Any stale
    error/result fields from a previous failed attempt are cleared
    first so the UI doesn't show old error text while it's queued.
    """
    meeting = get_meeting(meeting_id)
    _require_ownership(meeting, user_id)

    matches = [f for f in os.listdir(UPLOAD_DIR) if f.startswith(meeting_id)]
    if not matches:
        raise HTTPException(status_code=404, detail="Audio file not found on disk")
    original = [f for f in matches if "_compressed" not in f]
    file_path = os.path.join(UPLOAD_DIR, (original or matches)[0])

    meeting_type = meeting.get("meeting_type") or "General"
    language = meeting.get("language") or "auto"

    update_meeting(
        meeting_id,
        status="queued",
        summary=None,
        sentiment=None,
        action_items=None,
        email_subject=None,
        email_body=None,
    )
    background_tasks.add_task(_run_pipeline, meeting_id, file_path, meeting_type, language)

    return {"meeting_id": meeting_id, "status": "queued"}


@app.get("/api/meeting/{meeting_id}", response_model=MeetingResult)
async def get_meeting_result(meeting_id: str, user_id: str = Depends(get_current_user_id)):
    meeting = get_meeting(meeting_id)
    _require_ownership(meeting, user_id)
    return meeting


@app.patch("/api/meeting/{meeting_id}", response_model=MeetingResult)
async def update_meeting_result(meeting_id: str, request: UpdateMeetingRequest, user_id: str = Depends(get_current_user_id)):
    meeting = get_meeting(meeting_id)
    _require_ownership(meeting, user_id)

    fields_to_update = {}
    if request.action_items is not None:
        fields_to_update["action_items"] = json.dumps([item.model_dump() for item in request.action_items])
    if request.email_subject is not None:
        fields_to_update["email_subject"] = request.email_subject
    if request.email_body is not None:
        fields_to_update["email_body"] = request.email_body

    if fields_to_update:
        update_meeting(meeting_id, **fields_to_update)

    return get_meeting(meeting_id)


@app.get("/api/meetings")
async def get_all_meetings(user_id: str = Depends(get_current_user_id)):
    return list_meetings(user_id)


@app.post("/api/send-email/{meeting_id}")
async def send_followup_email(meeting_id: str, request: SendEmailRequest, user_id: str = Depends(get_current_user_id)):
    meeting = get_meeting(meeting_id)
    _require_ownership(meeting, user_id)
    if not meeting.get("email_subject"):
        raise HTTPException(status_code=400, detail="Meeting hasn't been processed yet")

    try:
        send_email(request.recipients, meeting["email_subject"], meeting["email_body"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    update_meeting(meeting_id, status="email_sent")
    return {"status": "sent", "recipients": request.recipients}


@app.post("/api/chat/{meeting_id}", response_model=ChatResponse)
async def chat_about_meeting(meeting_id: str, request: ChatRequest, user_id: str = Depends(get_current_user_id)):
    meeting = get_meeting(meeting_id)
    _require_ownership(meeting, user_id)
    if not meeting.get("transcript"):
        raise HTTPException(status_code=400, detail="This meeting hasn't been transcribed yet")

    try:
        answer = await answer_question(
            transcript=meeting["transcript"],
            summary=meeting.get("summary", ""),
            question=request.question,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"answer": answer}


# ---------------- Phase 4 ----------------

@app.post("/api/notion/sync/{meeting_id}", response_model=NotionSyncResponse)
async def sync_to_notion(meeting_id: str, user_id: str = Depends(get_current_user_id)):
    """Syncs this meeting's current action items into Notion as scheduled tasks."""
    meeting = get_meeting(meeting_id)
    _require_ownership(meeting, user_id)

    items = meeting.get("action_items") or []
    if not items:
        raise HTTPException(status_code=400, detail="This meeting has no action items to sync")

    try:
        result = await sync_action_items_to_notion(items, meeting_title=meeting["filename"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result


@app.get("/api/analytics", response_model=AnalyticsResponse)
async def analytics(user_id: str = Depends(get_current_user_id)):
    return get_analytics(user_id)


@app.post("/api/search", response_model=SearchResponse)
async def search_meetings(request: SearchRequest, user_id: str = Depends(get_current_user_id)):
    meetings = list_meetings_with_content(user_id)
    if not meetings:
        return {"answer": "You don't have any processed meetings yet.", "sources": []}

    try:
        result = await search_and_answer(meetings, request.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result


@app.get("/")
async def root():
    return {"message": "AI Meeting Assistant API is running"}