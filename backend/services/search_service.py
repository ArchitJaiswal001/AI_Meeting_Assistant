"""
Phase 4: Search across ALL of a user's past meetings.

Design choice, explained plainly: a true vector-embedding search
(FAISS + an embeddings API) is the "textbook" way to do this, but it
adds a separate embeddings API dependency, a vector store, and a
re-indexing pipeline — a lot of moving parts for what's still a
personal-scale tool (dozens to low-hundreds of meetings, not millions).

Instead, we use straightforward keyword-overlap scoring across each
meeting's summary + transcript to find the most relevant meetings,
then hand those meetings' content to the LLM to actually answer the
question. This is a lightweight, dependency-free retrieval step feeding
a real LLM synthesis step — the same RAG *pattern*, sized appropriately
for this project's actual scale. Swapping in real embeddings later
would only mean replacing `_score_meeting()` below.
"""
import re
from services.summarizer import answer_question_across_meetings

# Common words filtered out before scoring — without this, a query like
# "what was said about pricing" would match almost every meeting purely
# because they all contain words like "was" or "about", not because
# they're actually about pricing.
_STOPWORDS = {
    "a", "an", "the", "is", "was", "were", "are", "be", "been", "about",
    "what", "when", "where", "who", "how", "did", "does", "do", "in", "on",
    "at", "to", "for", "of", "and", "or", "it", "this", "that", "with",
    "said", "talk", "talked", "discuss", "discussed", "mention", "mentioned",
}


def _score_meeting(query_words: set, meeting: dict) -> int:
    text = f"{meeting.get('summary', '')} {meeting.get('transcript', '')}".lower()
    text_words = set(re.findall(r"[a-z0-9']+", text))
    return len(query_words & text_words)


def find_relevant_meetings(meetings: list, query: str, top_k: int = 3) -> list:
    """
    meetings: list of full meeting dicts (must include summary + transcript)
    Returns the top_k meetings most likely to be relevant, ranked by
    keyword overlap with the query. Meetings with a zero score are
    excluded entirely rather than padding out the result.
    """
    query_words = set(re.findall(r"[a-z0-9']+", query.lower())) - _STOPWORDS
    scored = [(m, _score_meeting(query_words, m)) for m in meetings]
    scored = [pair for pair in scored if pair[1] > 0]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [m for m, _score in scored[:top_k]]


async def search_and_answer(meetings: list, question: str) -> dict:
    relevant = find_relevant_meetings(meetings, question, top_k=3)

    if not relevant:
        return {
            "answer": "I couldn't find any past meetings related to that question.",
            "sources": [],
        }

    answer = await answer_question_across_meetings(relevant, question)

    return {
        "answer": answer,
        "sources": [{"id": m["id"], "filename": m["filename"]} for m in relevant],
    }