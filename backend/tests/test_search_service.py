"""Tests for the keyword-relevance search used by the cross-meeting search feature."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.search_service import find_relevant_meetings


def _meeting(id_, summary, transcript=""):
    return {"id": id_, "filename": f"{id_}.mp3", "summary": summary, "transcript": transcript}


def test_finds_meeting_matching_query_keywords():
    meetings = [
        _meeting("m1", "Discussed the Q3 pricing model and discounts"),
        _meeting("m2", "Talked about the new onboarding flow for users"),
    ]
    results = find_relevant_meetings(meetings, "what was said about pricing", top_k=3)
    assert len(results) == 1
    assert results[0]["id"] == "m1"


def test_excludes_meetings_with_zero_overlap():
    meetings = [_meeting("m1", "Completely unrelated topic about lunch orders")]
    results = find_relevant_meetings(meetings, "quarterly revenue forecast", top_k=3)
    assert results == []


def test_respects_top_k_limit():
    meetings = [_meeting(f"m{i}", "budget discussion budget") for i in range(5)]
    results = find_relevant_meetings(meetings, "budget", top_k=2)
    assert len(results) == 2


def test_ranks_stronger_match_first():
    meetings = [
        _meeting("weak", "budget was mentioned once"),
        _meeting("strong", "budget budget budget budget forecast"),
    ]
    results = find_relevant_meetings(meetings, "budget forecast", top_k=2)
    assert results[0]["id"] == "strong"