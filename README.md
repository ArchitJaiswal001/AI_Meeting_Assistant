# AI Meeting Assistant — Phase 1 (MVP)

Records or uploads a meeting → transcribes with Deepgram → summarizes and
extracts action items with an LLM via OpenRouter → sends a follow-up email.

## Prerequisites
- Python 3.10+
- Node.js 18+
- A [Deepgram](https://console.deepgram.com/) API key (free $200 credit on signup)
- An [OpenRouter](https://openrouter.ai/keys) API key
- A Gmail account with an [App Password](https://myaccount.google.com/apppasswords) generated

## Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# now open .env and fill in your real API keys

uvicorn main:app --reload
```

Backend runs at `http://localhost:8000`.
Visit `http://localhost:8000/docs` to see and test all API endpoints interactively.

## Frontend Setup

Open a **new terminal**:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

## How to Use It

1. Open `http://localhost:5173`
2. Either upload an audio/video file, or click "Record" to record live from your mic
3. Wait while it transcribes (Deepgram) and summarizes (OpenRouter)
4. Review the summary, action items, and drafted email
5. Enter recipient email(s), click "Send"

## Project Structure

```
backend/
  main.py                  API routes
  config.py                loads .env keys
  database.py               SQLite storage
  models.py                 request/response schemas
  services/
    transcription.py        Deepgram integration
    summarizer.py            OpenRouter LLM integration
    emailer.py                Gmail SMTP sending

frontend/
  src/
    App.jsx                  main state machine
    api.js                    backend API calls
    components/
      UploadPanel.jsx
      RecordPanel.jsx
      ResultsPanel.jsx
```

## Troubleshooting

- **"DEEPGRAM_API_KEY is not set"** → make sure you copied `.env.example` to `.env` and filled it in, and that `backend/.env` (not `.env.example`) has your real key.
- **CORS errors in browser console** → make sure the backend is running on port 8000 and frontend on 5173 (or update `VITE_API_URL` in a frontend `.env` file).
- **Gmail "Username and Password not accepted"** → you're likely using your real Gmail password instead of an App Password. Regenerate one at https://myaccount.google.com/apppasswords (requires 2-Step Verification enabled first).
- **Mic recording doesn't work** → browsers require HTTPS for mic access except on `localhost`, so this only works on `localhost` during local dev without extra config.

## Phase 2 Ideas (Add Later)
- Meeting history dashboard (list past meetings, list endpoint already exists: `GET /api/meetings`)
- Editable action items before sending
- Auto-sync to Notion/Trello
- Multi-language support
- RAG chatbot over past transcripts
