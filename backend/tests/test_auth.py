"""Tests for registration, login, and auth-protected access."""


def test_register_creates_account(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "newuser@example.com", "password": "securepass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "access_token" in data


def test_register_rejects_duplicate_email(client):
    payload = {"email": "dupe@example.com", "password": "securepass123"}
    client.post("/api/auth/register", json=payload)
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400


def test_register_rejects_short_password(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "shortpass@example.com", "password": "123"},
    )
    assert response.status_code == 400


def test_login_with_correct_credentials_succeeds(client):
    client.post(
        "/api/auth/register",
        json={"email": "logintest@example.com", "password": "securepass123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "logintest@example.com", "password": "securepass123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_with_wrong_password_fails(client):
    client.post(
        "/api/auth/register",
        json={"email": "wrongpass@example.com", "password": "securepass123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "wrongpass@example.com", "password": "incorrect"},
    )
    assert response.status_code == 401


def test_protected_route_without_token_is_rejected(client):
    response = client.get("/api/meetings")
    assert response.status_code == 401


def test_protected_route_with_valid_token_succeeds(client, auth_headers):
    response = client.get("/api/meetings", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []