"""
Handles turning an audio file into text using Deepgram's API.

Phase 3: accepts a language code so meetings in Hindi, Spanish, etc.
transcribe correctly instead of assuming English. "auto" lets Deepgram
detect the spoken language itself.
"""
import httpx
import aiofiles
from config import DEEPGRAM_API_KEY

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


async def transcribe_audio(file_path: str, language: str = "auto") -> str:
    if not DEEPGRAM_API_KEY:
        raise ValueError("DEEPGRAM_API_KEY is not set in your .env file")

    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "audio/*",
    }

    params = {
        "model": "nova-2",
        "smart_format": "true",
        "diarize": "true",
        "punctuate": "true",
    }

    if language and language != "auto":
        params["language"] = language
    else:
        params["detect_language"] = "true"

    async with aiofiles.open(file_path, "rb") as f:
        audio_bytes = await f.read()

    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(
            DEEPGRAM_URL, headers=headers, params=params, content=audio_bytes
        )

    if response.status_code != 200:
        raise RuntimeError(f"Deepgram error {response.status_code}: {response.text}")

    data = response.json()

    channel = data["results"]["channels"][0]
    alternative = channel["alternatives"][0]

    if "words" in alternative and alternative["words"]:
        transcript_lines = []
        current_speaker = None
        current_line = []

        for word in alternative["words"]:
            speaker = word.get("speaker", 0)
            if speaker != current_speaker:
                if current_line:
                    transcript_lines.append(
                        f"Speaker {current_speaker}: {' '.join(current_line)}"
                    )
                current_speaker = speaker
                current_line = [word["punctuated_word"]]
            else:
                current_line.append(word["punctuated_word"])

        if current_line:
            transcript_lines.append(f"Speaker {current_speaker}: {' '.join(current_line)}")

        return "\n".join(transcript_lines)

    return alternative.get("transcript", "")