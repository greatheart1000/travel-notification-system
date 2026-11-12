from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.observability import metrics
from app.modules.identity.models import LoginAttempt, now_iso
from app.modules.identity.repository import (
    LoginAttemptRepository,
    SessionRepository,
    UserRepository,
)
from app.modules.integration.persistence import JsonFileStore

UTC = UTC
PBKDF2_ROUNDS = 240_000
PBKDF2_SCHEME = "pbkdf2_sha256"
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")
PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")


class AuthError(Exception):
    """Domain error carrying an API-safe code and HTTP status."""

    def __init__(self, code: str, message: str = "", status_code: int = 400) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code
        self.status_code = status_code


def app_environment() -> str:
    return os.getenv("APP_ENV", "dev").strip().lower()


def token_fingerprint(token: str) -> str:
    secret = os.getenv("AUTH_TOKEN_SECRET", "").strip()
    if secret:
        return hmac.new(
            secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256
        ).hexdigest()
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_phone(raw: str) -> str:
    value = re.sub(r"[\s-]", "", str(raw or ""))
    if value.startswith("+86"):
        value = value[3:]
    elif value.startswith("0086"):
        value = value[4:]
    elif value.startswith("86") and len(value) == 13:
        value = value[2:]
    if not PHONE_PATTERN.fullmatch(value):
        raise AuthError("invalid_phone", "请输入有效的中国大陆手机号", 400)
    return value


@dataclass
class AuthService:
    users: dict[str, dict[str, str]] = field(default_factory=dict)
    access_tokens: dict[str, dict[str, str]] = field(default_factory=dict)
    refresh_tokens: dict[str, str] = field(default_factory=dict)
    store: JsonFileStore | None = None
    user_repository: UserRepository | None = None
    session_repository: SessionRepository | None = None
    login_attempt_repository: LoginAttemptRepository | None = None
    seed_demo_users: bool | None = None

    def __post_init__(self) -> None:
        if self.store is not None:
            self.user_repository = self.user_repository or UserRepository(self.store)
            self.session_repository = self.session_repository or SessionRepository(self.store)
            self.login_attempt_repository = (
                self.login_attempt_repository or LoginAttemptRepository(self.store)
            )
            persisted = self.user_repository.list_all()
            if persisted:
                self.users = {
                    str(item.get("username") or ""): dict(item)
                    for item in persisted
                    if str(item.get("username") or "")
                }
            else:
                seeded = self._seed_users()
                self.users = seeded
                for user in seeded.values():
                    self.user_repository.upsert(user)
            self._ensure_bootstrap_admin()
            self._ensure_bootstrap_operator()
            return

        if not self.users:
            self.users = self._seed_users()
        self._ensure_bootstrap_admin()
        self._ensure_bootstrap_operator()

    # ------------------------------------------------------------------ seed
    def _seed_users(self) -> dict[str, dict[str, str]]:
        environment = app_environment()
        seeded: dict[str, dict[str, str]] = {}
        if environment != "production" and self.seed_demo_users is not False:
            default_password = os.getenv("TRAVEL_NOTIFICATION_DEFAULT_PASSWORD", "123456")
            seeded = {
                "admin": {
                    "id": "user-001",
                    "username": "admin",
                    "email": "admin@travelhub.com",
                    "phone": "",
                    "role": "admin",
                    "tenant_id": "tenant-a",
                    "status": "active",
                    "password_hash": self.hash_password(default_password),
                    "created_at": "2026-04-11T00:00:00Z",
                },
                "user": {
                    "id": "user-002",
                    "username": "user",
                    "email": "user@travelhub.com",
                    "phone": "",
                    "role": "user",
                    "tenant_id": "tenant-a",
                    "status": "active",
                    "password_hash": self.hash_password(default_password),
                    "created_at": "2026-04-11T00:00:00Z",
                },
                "partner": {
                    "id": "user-003",
                    "username": "partner",
                    "email": "partner@travelhub.com",
                    "phone": "",
                    "role": "user",
                    "tenant_id": "tenant-b",
                    "status": "active",
                    "password_hash": self.hash_password(default_password),
                    "created_at": "2026-04-11T00:00:00Z",
                },
            }

        bootstrap_username = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "admin").strip()
        bootstrap_password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
        if bootstrap_username and bootstrap_password:
            self.validate_password(bootstrap_password)
            tenant_id = os.getenv("BOOTSTRAP_TENANT_ID", "tenant-a").strip() or "tenant-a"
            seeded[bootstrap_username] = {
                "id": seeded.get(bootstrap_username, {}).get("id")
                or f"user-{uuid4().hex[:12]}",
                "username": bootstrap_username,
                "email": os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip(),
                "phone": os.getenv("BOOTSTRAP_ADMIN_PHONE", "").strip(),
                "role": "admin",
                "tenant_id": tenant_id,
                "status": "active",
                "password_hash": self.hash_password(bootstrap_password),
                "created_at": now_iso(),
            }
        elif environment == "production" and not seeded:
            raise RuntimeError(
                "No users found. Set BOOTSTRAP_ADMIN_USERNAME and "
                "BOOTSTRAP_ADMIN_PASSWORD to create the first administrator."
            )

        operator_username = os.getenv("BOOTSTRAP_OPERATOR_USERNAME", "").strip()
        operator_password = os.getenv("BOOTSTRAP_OPERATOR_PASSWORD", "")
        if operator_username and operator_password:
            self.validate_password(operator_password)
            seeded[operator_username] = {
                "id": seeded.get(operator_username, {}).get("id")
                or f"user-{uuid4().hex[:12]}",
                "username": operator_username,
                "email": os.getenv("BOOTSTRAP_OPERATOR_EMAIL", "").strip(),
                "phone": "",
                "role": "operator",
                "tenant_id": os.getenv("BOOTSTRAP_OPERATOR_TENANT_ID", "platform").strip()
                or "platform",
                "status": "active",
                "password_hash": self.hash_password(operator_password),
                "created_at": now_iso(),
            }
        return seeded

    def _ensure_bootstrap_operator(self) -> None:
        username = os.getenv("BOOTSTRAP_OPERATOR_USERNAME", "").strip()
        password = os.getenv("BOOTSTRAP_OPERATOR_PASSWORD", "")
        if not username or not password or username in self.users:
            return
        self.create_user(
            tenant_id=os.getenv("BOOTSTRAP_OPERATOR_TENANT_ID", "platform").strip()
            or "platform",
            username=username,
            password=password,
            email=os.getenv("BOOTSTRAP_OPERATOR_EMAIL", "").strip(),
            role="operator",
        )

    def _ensure_bootstrap_admin(self) -> None:
        username = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "").strip()
        password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
        if not username or not password or username in self.users:
            return
        self.create_user(
            tenant_id=os.getenv("BOOTSTRAP_TENANT_ID", "tenant-a").strip() or "tenant-a",
            username=username,
            password=password,
            email=os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip(),
            phone=os.getenv("BOOTSTRAP_ADMIN_PHONE", "").strip(),
            role="admin",
        )

    # -------------------------------------------------------------- passwords
    @staticmethod
    def _is_pbkdf2_hash(hash_value: str) -> bool:
        return hash_value.startswith(f"{PBKDF2_SCHEME}$")

    @staticmethod
    def _pbkdf2_parts(hash_value: str) -> tuple[int, bytes, bytes] | None:
        parts = hash_value.split("$")
        if len(parts) != 4 or parts[0] != PBKDF2_SCHEME:
            return None
        try:
            rounds = int(parts[1])
            salt = base64.b64decode(parts[2].encode("utf-8"))
            digest = base64.b64decode(parts[3].encode("utf-8"))
        except (ValueError, TypeError):
            return None
        return rounds, salt, digest

    @staticmethod
    def hash_password(raw_password: str) -> str:
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            raw_password.encode("utf-8"),
            salt,
            PBKDF2_ROUNDS,
        )
        salt_b64 = base64.b64encode(salt).decode("utf-8")
        digest_b64 = base64.b64encode(digest).decode("utf-8")
        return f"{PBKDF2_SCHEME}${PBKDF2_ROUNDS}${salt_b64}${digest_b64}"

    @staticmethod
    def _legacy_sha256(raw_password: str) -> str:
        return hashlib.sha256(raw_password.encode("utf-8")).hexdigest()

    def validate_password(self, raw_password: str) -> None:
        try:
            minimum = int(os.getenv("AUTH_MIN_PASSWORD_LENGTH", "8"))
        except ValueError:
            minimum = 8
        if app_environment() in {"dev", "test", "local"}:
            minimum = min(minimum, 6)
        if len(raw_password or "") < minimum:
            raise AuthError(
                "password_too_short",
                f"密码长度至少 {minimum} 位",
                400,
            )

    def verify_password(self, username: str, raw_password: str) -> bool:
        user = self.users.get(username)
        if user is None:
            return False
        expected = str(user.get("password_hash", ""))
        if self._is_pbkdf2_hash(expected):
            parsed = self._pbkdf2_parts(expected)
            if parsed is None:
                return False
            rounds, salt, digest = parsed
            actual = hashlib.pbkdf2_hmac(
                "sha256",
                raw_password.encode("utf-8"),
                salt,
                rounds,
            )
            return hmac.compare_digest(actual, digest)

        # Backward compatibility for old sha256 hashes; upgrade on successful login.
        legacy_ok = hmac.compare_digest(expected, self._legacy_sha256(raw_password))
        if legacy_ok:
            self._update_user_fields(username, password_hash=self.hash_password(raw_password))
        return legacy_ok

    # ------------------------------------------------------------------ users
    def _update_user_fields(self, username: str, **fields: object) -> None:
        user = self.users.get(username)
        if user is None:
            return
        for key, value in fields.items():
            user[key] = value  # type: ignore[assignment]
        user["updated_at"] = now_iso()
        if self.user_repository is not None:
            self.user_repository.upsert(user)

    def create_user(
        self,
        *,
        tenant_id: str,
        username: str,
        password: str,
        email: str = "",
        phone: str = "",
        role: str = "user",
    ) -> dict[str, str]:
        username = str(username or "").strip()
        if not USERNAME_PATTERN.fullmatch(username):
            raise AuthError(
                "invalid_username",
                "用户名需为 3-32 位字母、数字、下划线、点或短横线",
                400,
            )
        if username in self.users:
            raise AuthError("username_taken", "用户名已存在", 409)
        self.validate_password(password)
        if phone:
            normalized = normalize_phone(phone)
            if self.find_by_phone(normalized) is not None:
                raise AuthError("phone_taken", "该手机号已注册", 409)
            phone = normalized
        if role not in {"admin", "user", "operator"}:
            raise AuthError("invalid_role", "无效角色", 400)

        user = {
            "id": f"user-{uuid4().hex[:12]}",
            "username": username,
            "email": str(email or "").strip(),
            "phone": phone,
            "role": role,
            "tenant_id": str(tenant_id or "").strip(),
            "status": "active",
            "password_hash": self.hash_password(password),
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "last_login_at": "",
        }
        self.users[username] = user
        if self.user_repository is not None:
            self.user_repository.upsert(user)
        return self.get_user_profile(username) or {}

    def find_by_phone(self, phone: str) -> dict[str, str] | None:
        for user in self.users.values():
            if str(user.get("phone") or "") == phone:
                return user
        return None

    def get_user(self, username: str) -> dict[str, str] | None:
        return self.users.get(username)

    def get_user_by_id(self, user_id: str) -> dict[str, str] | None:
        for user in self.users.values():
            if str(user.get("id") or "") == user_id:
                return user
        return None

    def list_users(self, tenant_id: str | None = None) -> list[dict[str, str]]:
        users = [
            self.get_user_profile(username) or {}
            for username in sorted(self.users)
        ]
        if tenant_id is not None:
            users = [user for user in users if user.get("tenant_id") == tenant_id]
        return users

    def update_user(
        self,
        username: str,
        *,
        email: str | None = None,
        phone: str | None = None,
        role: str | None = None,
        status: str | None = None,
    ) -> dict[str, str] | None:
        user = self.users.get(username)
        if user is None:
            return None
        fields: dict[str, object] = {}
        if email is not None:
            fields["email"] = str(email).strip()
        if phone is not None:
            normalized = normalize_phone(phone) if phone else ""
            if normalized and normalized != str(user.get("phone") or ""):
                existing = self.find_by_phone(normalized)
                if existing is not None and existing is not user:
                    raise AuthError("phone_taken", "该手机号已注册", 409)
            fields["phone"] = normalized
        if role is not None:
            if role not in {"admin", "user", "operator"}:
                raise AuthError("invalid_role", "无效角色", 400)
            fields["role"] = role
        if status is not None:
            if status not in {"active", "disabled"}:
                raise AuthError("invalid_status", "无效状态", 400)
            fields["status"] = status
        next_role = str(fields.get("role", user.get("role") or "user"))
        next_status = str(fields.get("status", user.get("status") or "active"))
        if (user.get("role") == "admin") and (
            next_role != "admin" or next_status != "active"
        ):
            peers = [
                peer
                for peer in self.users.values()
                if str(peer.get("tenant_id") or "") == str(user.get("tenant_id") or "")
                and str(peer.get("role") or "") == "admin"
                and str(peer.get("status") or "active") == "active"
                and str(peer.get("username") or "") != username
            ]
            if not peers:
                raise AuthError(
                    "last_admin",
                    "企业至少需要保留一名启用状态的管理员",
                    400,
                )
        self._update_user_fields(username, **fields)
        return self.get_user_profile(username)

    def change_password(self, username: str, new_password: str) -> bool:
        user = self.users.get(username)
        if user is None:
            return False
        self.validate_password(new_password)
        self._update_user_fields(username, password_hash=self.hash_password(new_password))
        self.revoke_sessions(username)
        return True

    # ----------------------------------------------------------------- tokens
    def issue_token_pair(self, username: str) -> dict[str, object]:
        access_token = f"tk-{uuid4().hex}"
        refresh_token = f"rf-{uuid4().hex}"
        expires_at = datetime.now(tz=UTC) + timedelta(hours=24)
        self.access_tokens[access_token] = {
            "username": username,
            "expires_at": expires_at.isoformat(),
            "refresh_token": refresh_token,
        }
        self.refresh_tokens[refresh_token] = username
        if self.session_repository is not None:
            self.session_repository.upsert(
                {
                    "access_token_hash": token_fingerprint(access_token),
                    "refresh_token_hash": token_fingerprint(refresh_token),
                    "username": username,
                    "expires_at": expires_at.isoformat(),
                    "refresh_expires_at": (
                        datetime.now(tz=UTC) + timedelta(days=30)
                    ).isoformat(),
                    "created_at": now_iso(),
                }
            )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 86400,
        }

    def login(
        self,
        username: str,
        password: str,
        *,
        client_ip: str = "",
    ) -> dict[str, object] | None:
        user = self.users.get(username)
        if user is None or str(user.get("status") or "active") != "active":
            metrics.inc("auth_login_failures_total", reason="unknown_or_disabled")
            self._record_login_attempt(username, client_ip, ok=False)
            return None
        if not self.verify_password(username, password):
            metrics.inc("auth_login_failures_total", reason="bad_password")
            self._record_login_attempt(username, client_ip, ok=False)
            return None
        metrics.inc("auth_logins_total")
        self._record_login_attempt(username, client_ip, ok=True)
        self._update_user_fields(username, last_login_at=now_iso())
        return self.issue_token_pair(username)

    def _record_login_attempt(self, identifier: str, client_ip: str, *, ok: bool) -> None:
        if self.login_attempt_repository is None or not identifier:
            return
        self.login_attempt_repository.record(
            LoginAttempt(
                id=f"login-{uuid4().hex}",
                identifier=identifier,
                client_ip=client_ip,
                ok=ok,
                created_at=now_iso(),
            )
        )

    def login_rate_limited(
        self,
        identifier: str,
        *,
        client_ip: str = "",
        window_minutes: int = 15,
        max_failures: int = 5,
    ) -> bool:
        if self.login_attempt_repository is None:
            return False
        since = (datetime.now(tz=UTC) - timedelta(minutes=window_minutes)).isoformat()
        if self.login_attempt_repository.count_failures(identifier, since) >= max_failures:
            return True
        return (
            self.login_attempt_repository.count_ip_failures(client_ip, since)
            >= max_failures * 3
        )

    def authenticate(self, token: str) -> dict[str, str] | None:
        session = self.access_tokens.get(token)
        username: str | None = None
        expires_at_raw: str | None = None
        if session is not None:
            username = session.get("username")
            expires_at_raw = session.get("expires_at")
        elif self.session_repository is not None:
            stored = self.session_repository.get_by_access_hash(token_fingerprint(token))
            if stored is not None:
                username = str(stored.get("username") or "")
                expires_at_raw = str(stored.get("expires_at") or "")
                if username:
                    self.access_tokens[token] = {
                        "username": username,
                        "expires_at": expires_at_raw,
                    }
        if not username or not expires_at_raw:
            return None
        try:
            expires_at = datetime.fromisoformat(expires_at_raw)
        except ValueError:
            return None
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(tz=UTC):
            self.logout(token)
            return None
        profile = self.get_user_profile(username)
        if profile is None or str(profile.get("status") or "active") != "active":
            return None
        return profile

    def refresh(self, refresh_token: str) -> dict[str, object] | None:
        username = self.refresh_tokens.get(refresh_token)
        if username is None and self.session_repository is not None:
            stored = self.session_repository.get_by_refresh_hash(
                token_fingerprint(refresh_token)
            )
            if stored is not None:
                refresh_expires = str(stored.get("refresh_expires_at") or "")
                if refresh_expires:
                    try:
                        expires_at = datetime.fromisoformat(refresh_expires)
                    except ValueError:
                        expires_at = None
                    if expires_at is not None and expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=UTC)
                    if expires_at is not None and expires_at < datetime.now(tz=UTC):
                        self.session_repository.delete_by_refresh_hash(
                            token_fingerprint(refresh_token)
                        )
                        return None
                username = str(stored.get("username") or "")
                if username:
                    self.refresh_tokens[refresh_token] = username
        if username is None or username not in self.users:
            return None
        if str(self.users[username].get("status") or "active") != "active":
            return None
        # Refresh-token rotation: a used refresh token must not remain valid.
        self._revoke_refresh_token(refresh_token)
        return self.issue_token_pair(username)

    def _revoke_refresh_token(self, refresh_token: str) -> None:
        self.refresh_tokens.pop(refresh_token, None)
        for access_token, session in list(self.access_tokens.items()):
            if session.get("refresh_token") == refresh_token:
                self.access_tokens.pop(access_token, None)
        if self.session_repository is not None:
            self.session_repository.delete_by_refresh_hash(
                token_fingerprint(refresh_token)
            )

    def logout(self, access_token: str) -> None:
        session = self.access_tokens.pop(access_token, None)
        refresh_token = str((session or {}).get("refresh_token") or "")
        if refresh_token:
            self.refresh_tokens.pop(refresh_token, None)
        if self.session_repository is not None:
            fingerprint = token_fingerprint(access_token)
            stored = self.session_repository.get_by_access_hash(fingerprint)
            if stored is not None:
                stored_refresh_hash = str(stored.get("refresh_token_hash") or "")
                for token, owner in list(self.refresh_tokens.items()):
                    if token_fingerprint(token) == stored_refresh_hash:
                        self.refresh_tokens.pop(token, None)
            self.session_repository.delete_by_access_hash(fingerprint)

    def revoke_sessions(self, username: str) -> None:
        for token in [
            token
            for token, session in self.access_tokens.items()
            if session.get("username") == username
        ]:
            self.access_tokens.pop(token, None)
        for token, owner in list(self.refresh_tokens.items()):
            if owner == username:
                self.refresh_tokens.pop(token, None)
        if self.session_repository is not None:
            self.session_repository.delete_for_username(username)

    def get_user_profile(self, username: str) -> dict[str, str] | None:
        user = self.users.get(username)
        if user is None:
            return None
        return {
            "id": str(user.get("id") or username),
            "username": user["username"],
            "email": str(user.get("email") or ""),
            "phone": str(user.get("phone") or ""),
            "role": str(user.get("role") or "user"),
            "tenant_id": str(user.get("tenant_id") or ""),
            "status": str(user.get("status") or "active"),
            "created_at": str(user.get("created_at") or ""),
        }
