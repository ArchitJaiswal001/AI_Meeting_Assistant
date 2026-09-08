"""
Tests for _parse_json_safely — the function that strips markdown code
fences LLMs sometimes wrap around JSON output despite instructions.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.summarizer import _parse_json_safely


def test_parses_clean_json():
    raw = '{"summary": "Test summary", "action_items": []}'
    result = _parse_json_safely(raw)
    assert result["summary"] == "Test summary"


def test_strips_json_code_fence():
    raw = '```json\n{"summary": "Test"}\n```'
    result = _parse_json_safely(raw)
    assert result["summary"] == "Test"


def test_strips_plain_code_fence():
    raw = '```\n{"summary": "Test"}\n```'
    result = _parse_json_safely(raw)
    assert result["summary"] == "Test"


def test_raises_clear_error_on_invalid_json():
    with pytest.raises(RuntimeError, match="Could not parse"):
        _parse_json_safely("this is not json at all")


def test_handles_whitespace_around_json():
    raw = '   \n  {"summary": "Test"}  \n  '
    result = _parse_json_safely(raw)
    assert result["summary"] == "Test"