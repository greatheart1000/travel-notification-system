from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import uuid4

UTC = UTC


@dataclass(slots=True)
class AuthService:
    users: dict[str, dict[str, str]] = field(default_factory=dict)
    access_tokens: dict[str, dict[str, str]] = field(default_factory=dict)
    refresh_tokens: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.users:
            return
        self.users = {
            "admin": {
                "id": "user-001",
                "username": "admin",
                "email": "admin@travelhub.com",
                "role": "admin",
                "password_hash": self.hash_password("123456"),
                "created_at": "2026-04-11T00:00:00Z",
            },
            "user": {
                "id": "user-002",
                "username": "user",
                "email": "user@travelhub.com",
                "role": "user",
                "password_hash": self.hash_password("123456"),
                "created_at": "2026-04-11T00:00:00Z",
            },
        }

    @staticmethod
    def hash_password(raw_password: str) -> str:
        return hashlib.sha256(raw_password.encode("utf-8")).hexdigest()

    def verify_password(self, username: str, raw_password: str) -> bool:
        user = self.users.get(username)
        if user is None:
            return False
        expected = user.get("password_hash", "")
        return hmac.compare_digest(expected, self.hash_password(raw_password))

    def issue_token_pair(self, username: str) -> dict[str, object]:
        access_token = f"tk-{uuid4().hex}"
        refresh_token = f"rf-{uuid4().hex}"
        expires_at = datetime.now(tz=UTC) + timedelta(hours=24)
        self.access_tokens[access_token] = {
            "username": username,
            "expires_at": expires_at.isoformat(),
        }
        self.refresh_tokens[refresh_token] = username
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 86400,
        }

    def login(self, username: str, password: str) -> dict[str, object] | None:
        if username not in self.users:
            return None
        if not self.verify_password(username, password):
            return None
        return self.issue_token_pair(username)

    def authenticate(self, token: str) -> dict[str, str] | None:
        session = self.access_tokens.get(token)
        if session is None:
            return None
        expires_at = datetime.fromisoformat(session["expires_at"])
        if expires_at < datetime.now(tz=UTC):
            self.access_tokens.pop(token, None)
            return None
        username = session["username"]
        return self.get_user_profile(username)

    def refresh(self, refresh_token: str) -> dict[str, object] | None:
        username = self.refresh_tokens.get(refresh_token)
        if username is None or username not in self.users:
            return None
        return self.issue_token_pair(username)

    def logout(self, access_token: str) -> None:
        self.access_tokens.pop(access_token, None)

    def get_user_profile(self, username: str) -> dict[str, str] | None:
        user = self.users.get(username)
        if user is None:
            return None
        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "created_at": user["created_at"],
        }
