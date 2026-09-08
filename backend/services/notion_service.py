"""
Phase 4: Notion scheduling feature.

Syncs a meeting's action items into a Notion database as individual
task pages — each with a title, owner, due date, and status — so
action items land where teams already track work, instead of living
only inside this app.

Setup (one-time, done by the user):
  1. Go to https://www.notion.so/my-integrations and create an
     integration -> copy its "Internal Integration Secret" into
     NOTION_API_KEY in .env
  2. Create a Notion database with these properties (case-sensitive):
       - Name        (Title)
       - Owner       (Text)
       - Due Date    (Date)
       - Status      (Select, with a "Not started" option)
       - Meeting     (Text)
  3. Share that database with the integration (••• menu -> Connections)
  4. Copy the database ID from its URL into NOTION_DATABASE_ID in .env

We use plain httpx calls to Notion's REST API rather than the official
notion-client SDK — one less dependency, and the API surface we need
(creating pages) is small enough that raw requests are simpler to read
and debug.
"""
import httpx
from datetime import datetime
from config import NOTION_API_KEY, NOTION_DATABASE_ID

NOTION_API_URL = "https://api.notion.com/v1/pages"
NOTION_VERSION = "2022-06-28"


def _parse_due_date(deadline: str | None) -> str | None:
    """
    Action item deadlines from the LLM are free-text ("Friday", "next
    week", or None) — Notion's Date property needs an ISO date. Rather
    than guessing at fuzzy dates (error-prone), we only set a real date
    when the LLM already gave us one in a parseable format, and fall
    back to putting the original text in the task title otherwise so
    no information is silently lost.
    """
    if not deadline:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(deadline.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


async def sync_action_items_to_notion(action_items: list, meeting_title: str) -> dict:
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        raise ValueError(
            "NOTION_API_KEY or NOTION_DATABASE_ID is not set in your .env file. "
            "See services/notion_service.py for setup steps."
        )

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }

    created_pages = []
    failed_items = []

    async with httpx.AsyncClient(timeout=30) as client:
        for item in action_items:
            task = item.get("task") if isinstance(item, dict) else item.task
            owner = item.get("owner") if isinstance(item, dict) else item.owner
            deadline = item.get("deadline") if isinstance(item, dict) else item.deadline

            iso_date = _parse_due_date(deadline)
            title = task if iso_date or not deadline else f"{task} ({deadline})"

            properties = {
                "Name": {"title": [{"text": {"content": title}}]},
                "Owner": {"rich_text": [{"text": {"content": owner or "Unassigned"}}]},
                "Status": {"select": {"name": "Not started"}},
                "Meeting": {"rich_text": [{"text": {"content": meeting_title}}]},
            }
            if iso_date:
                properties["Due Date"] = {"date": {"start": iso_date}}

            payload = {"parent": {"database_id": NOTION_DATABASE_ID}, "properties": properties}

            response = await client.post(NOTION_API_URL, headers=headers, json=payload)

            if response.status_code == 200:
                created_pages.append({
                    "task": task,
                    "url": response.json().get("url", ""),
                })
            else:
                failed_items.append({"task": task, "error": response.text})

    return {
        "synced_count": len(created_pages),
        "failed_count": len(failed_items),
        "created_pages": created_pages,
        "failed_items": failed_items,
    }