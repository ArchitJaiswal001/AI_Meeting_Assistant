"""
Sends the meeting transcript to an LLM (via OpenRouter) and asks it to
return a structured summary + action items + a draft follow-up email —
all in one call, as JSON.
"""
import httpx
import json
import re
from config import OPENROUTER_API_KEY, OPENROUTER_MODEL

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MEETING_TYPE_GUIDANCE = {
    "General": "",
    "Standup": (
        "This is a daily standup. In the summary, organize around what each "
        "person completed, what they're doing next, and any blockers raised. "
        "Action items should prioritize unblocking people over general tasks."
    ),
    "Client Call": (
        "This is a client call. In the summary, emphasize commitments made to "
        "the client, concerns or objections they raised, and agreed next steps. "
        "Action items should reflect promises made that need to be delivered on."
    ),
    "Brainstorm": (
        "This is a brainstorming session. In the summary, list the key ideas "
        "generated and which ones the group leaned toward pursuing. "
        "Action items should be about validating or developing the strongest ideas."
    ),
}

SYSTEM_PROMPT_TEMPLATE = """You are an assistant that processes meeting transcripts.

{type_guidance}

Given a transcript, return ONLY a valid JSON object (no markdown, no
extra text) with this exact structure:

{{
  "summary": "A concise 3-5 sentence summary of what was discussed and decided",
  "sentiment": "A short phrase (5-10 words) describing the overall tone, e.g. 'Collaborative and upbeat' or 'Tense, some disagreement on timeline'",
  "action_items": [
    {{"task": "short task description", "owner": "person name or 'Unassigned'", "deadline": "date/day mentioned or null"}}
  ],
  "email_subject": "a short, clear subject line for the follow-up email",
  "email_body": "a professional follow-up email body that includes the summary and lists action items with owners"
}}

Rules:
- If speakers are labeled (Speaker 0, Speaker 1...), use context to infer
  real names if mentioned in the transcript, otherwise keep speaker labels.
- If no deadline was mentioned for a task, set deadline to null.
- Keep the email body friendly and professional, formatted with line breaks.
- Return ONLY the JSON object. No explanation, no markdown code fences.
"""


async def summarize_transcript(transcript: str, meeting_type: str = "General", language: str = "auto") -> dict:
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set in your .env file")

    if not transcript or not transcript.strip():
        raise ValueError(
            "Transcript is empty — Deepgram returned no speech. "
            "Try a longer/clearer recording."
        )

    language_instruction = ""
    if language and language != "auto":
        language_names = {
            "en": "English", "hi": "Hindi", "es": "Spanish", "fr": "French",
            "de": "German", "pt": "Portuguese", "ja": "Japanese", "zh": "Chinese",
        }
        lang_name = language_names.get(language, language)
        language_instruction = (
            f"\nWrite the summary, action items, and email entirely in {lang_name}, "
            f"since that is the language of this meeting."
        )

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        type_guidance=MEETING_TYPE_GUIDANCE.get(meeting_type, "") + language_instruction
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Transcript:\n\n{transcript}"},
        ],
        "temperature": 0.3,
        "max_tokens": 1200,
    }

    last_error = None
    for attempt in range(2):
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(OPENROUTER_URL, headers=headers, json=payload)

        if response.status_code != 200:
            raise RuntimeError(f"OpenRouter error {response.status_code}: {response.text}")

        data = response.json()

        try:
            choice = data["choices"][0]
            raw_content = choice["message"]["content"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Unexpected OpenRouter response shape: {data}") from e

        if raw_content:
            return _parse_json_safely(raw_content)

        finish_reason = choice.get("finish_reason", "unknown")
        last_error = f"Empty response from model (finish_reason={finish_reason})"
        print(f"[summarizer] Attempt {attempt + 1} got empty content, retrying... ({last_error})")

    raise RuntimeError(f"Model returned an empty response after 2 attempts. {last_error}")


async def answer_question(transcript: str, summary: str, question: str) -> str:
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set in your .env file")

    system_prompt = (
        "You answer questions about a specific meeting using ONLY the transcript "
        "and summary provided below. If the answer isn't in the transcript, say "
        "so clearly instead of guessing. Keep answers concise (2-4 sentences) "
        "unless the question asks for more detail."
    )

    context = f"MEETING SUMMARY:\n{summary}\n\nFULL TRANSCRIPT:\n{transcript}"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{context}\n\nQUESTION: {question}"},
        ],
        "temperature": 0.2,
        "max_tokens": 400,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(OPENROUTER_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise RuntimeError(f"OpenRouter error {response.status_code}: {response.text}")

    data = response.json()
    try:
        answer = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected OpenRouter response shape: {data}") from e

    if not answer:
        raise RuntimeError("Model returned an empty answer — try rephrasing the question.")

    return answer.strip()


async def answer_question_across_meetings(meetings: list, question: str) -> str:
    """
    Phase 4: powers the "Search all meetings" feature. Given a small
    set of candidate meetings (already narrowed down by keyword
    relevance in search_service.py), synthesizes one answer that may
    draw on any of them, citing which meeting each part came from.
    """
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set in your .env file")

    context_blocks = []
    for m in meetings:
        context_blocks.append(
            f"--- MEETING: {m.get('filename', 'Untitled')} "
            f"(created {m.get('created_at', '')[:10]}) ---\n"
            f"Summary: {m.get('summary', '')}\n"
            f"Transcript: {m.get('transcript', '')[:4000]}"
        )
    context = "\n\n".join(context_blocks)

    system_prompt = (
        "You answer questions using ONLY the meeting excerpts provided below, "
        "which may span multiple different meetings. When relevant, mention "
        "which meeting (by filename) your answer is drawn from. If none of "
        "the meetings answer the question, say so clearly instead of guessing. "
        "Keep answers concise (3-5 sentences) unless more detail is requested."
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{context}\n\nQUESTION: {question}"},
        ],
        "temperature": 0.2,
        "max_tokens": 500,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(OPENROUTER_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise RuntimeError(f"OpenRouter error {response.status_code}: {response.text}")

    data = response.json()
    try:
        answer = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected OpenRouter response shape: {data}") from e

    if not answer:
        raise RuntimeError("Model returned an empty answer.")

    return answer.strip()


def _parse_json_safely(raw_text: str) -> dict:
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```json\s*|\s*```$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^```\s*|\s*```$", "", cleaned, flags=re.MULTILINE)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Could not parse LLM response as JSON: {e}\nRaw response: {raw_text}")