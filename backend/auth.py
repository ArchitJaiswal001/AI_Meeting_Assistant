"""
Phase 3: Authentication.

Two jobs:
  1. Hash/verify passwords with bcrypt (never store plain-text passwords)
  2. Create/verify JWT tokens so the frontend can prove "I'm logged in
     as user X" on every request, without sending the password every time

Login flow:
  - User posts email+password to /api/auth/login
  - We verify the password against the stored hash
  - We hand back a signed JWT containing their user_id
  - Frontend stores that token and sends it as
    "Authorization: Bearer <token>" on every subsequent request
  - get_current_user_id() below reads and verifies that header
"""
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Header, HTTPException
from config import JWT_SECRET_KEY, JWT_EXPIRE_HOURS


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired — please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")


def get_current_user_id(authorization: str = Header(None)) -> str:
    """
    FastAPI dependency — add `user_id: str = Depends(get_current_user_id)`
    to any route to require login and get the calling user's id.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_access_token(token)
    return payload["sub"]