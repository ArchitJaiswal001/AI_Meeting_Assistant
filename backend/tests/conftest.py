"""
Shared pytest fixtures. The most important one is `client`, which uses
a temporary SQLite database (not your real meetings.db) so running
tests never touches or wipes your actual data.
"""
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture()
def client(monkeypatch):
    """
    Spins up a FastAPI TestClient backed by a fresh temp SQLite file
    per test, so tests are isolated from each other and from your
    real database.
    """
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")

    import config
    monkeypatch.setattr(config, "DATABASE_PATH", db_path)

    import database
    monkeypatch.setattr(database, "DATABASE_PATH", db_path)
    # main.py only calls init_db() once, at first import — since pytest
    # reuses the cached module across tests, later tests would otherwise
    # get a fresh empty temp file with no tables. Calling it explicitly
    # here guarantees every test starts with a properly initialized DB.
    database.init_db()

    from fastapi.testclient import TestClient
    import main
    test_client = TestClient(main.app)

    yield test_client

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture()
def auth_headers(client):
    """Registers a test user and returns ready-to-use auth headers."""
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}