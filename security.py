import secrets
from datetime import datetime, timedelta, timezone

SESSION_TTL_DAYS = 30


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def session_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
