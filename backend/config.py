"""
Loads all secrets/config from a .env file so you never hardcode
API keys in your code (important for pushing to GitHub safely).
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Deepgram (speech-to-text)
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")

# OpenRouter (LLM for summarization + action items)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

# Gmail SMTP (sending follow-up emails)
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# Phase 3: Auth — used to sign/verify login tokens (JWTs).
# IMPORTANT: set a real random value in your .env for production use.
# A missing value falls back to a dev-only default so the app still
# runs locally, but this must never be used outside your own machine.
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-insecure-secret-change-me")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

# Where uploaded/recorded audio files are stored
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# Phase 4: Notion — used to sync action items into a Notion database as
# scheduled tasks. Get these from https://www.notion.so/my-integrations
# and by sharing your target database with that integration.
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")


# SQLite database file path
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "meetings.db")