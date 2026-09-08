"""
Pydantic models define the exact shape of data going in/out of the API.
"""
from pydantic import BaseModel, EmailStr
from typing import List, Optional

MEETING_TYPES = ["General", "Standup", "Client Call", "Brainstorm"]

SUPPORTED_LANGUAGES = {
    "auto": "Auto-detect",
    "en": "English",
    "hi": "Hindi",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "ja": "Japanese",
    "zh": "Chinese",
}


class ActionItem(BaseModel):
    task: str
    owner: str
    deadline: Optional[str] = None
    done: bool = False  # Phase 4: completion tracking


class MeetingResult(BaseModel):
    id: str
    filename: str
    status: str
    meeting_type: Optional[str] = "General"
    language: Optional[str] = "auto"
    transcript: Optional[str] = None
    summary: Optional[str] = None
    sentiment: Optional[str] = None
    action_items: Optional[List[ActionItem]] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None


class SendEmailRequest(BaseModel):
    recipients: List[str]


class UpdateMeetingRequest(BaseModel):
    action_items: Optional[List[ActionItem]] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    email: str


# ---------------- Phase 4 ----------------

class NotionSyncResponse(BaseModel):
    synced_count: int
    failed_count: int
    created_pages: List[dict]
    failed_items: List[dict]


class SearchRequest(BaseModel):
    question: str


class SearchResponse(BaseModel):
    answer: str
    sources: List[dict]


class AnalyticsResponse(BaseModel):
    total_meetings: int
    by_type: dict
    by_status: dict
    per_week: List[dict]
    total_action_items: int
    completed_action_items: int