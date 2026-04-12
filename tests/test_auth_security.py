from __future__ import annotations

from app.modules.integration.auth import AuthService


def test_password_hash_uses_pbkdf2_scheme() -> None:
    hashed = AuthService.hash_password("example-password")
    assert hashed.startswith("pbkdf2_sha256$")


def test_verify_password_supports_legacy_sha256_and_upgrades_hash() -> None:
    service = AuthService(
        users={
            "legacy": {
                "id": "u-1",
                "username": "legacy",
                "email": "legacy@example.com",
                "role": "user",
                "tenant_id": "tenant-a",
                "password_hash": AuthService._legacy_sha256("123456"),
                "created_at": "2026-01-01T00:00:00Z",
            }
        }
    )

    assert service.verify_password("legacy", "123456") is True
    assert service.users["legacy"]["password_hash"].startswith("pbkdf2_sha256$")
