from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(tz=UTC).isoformat()


@dataclass(slots=True)
class Tenant:
    id: str
    name: str
    status: str = "active"  # active | suspended
    contact_name: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    invoice_title: str = ""
    tax_id: str = ""
    invoice_address: str = ""
    invoice_phone: str = ""
    invoice_bank_name: str = ""
    invoice_bank_account: str = ""
    invoice_email: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.id,
            "name": self.name,
            "status": self.status,
            "contact_name": self.contact_name,
            "contact_phone": self.contact_phone,
            "contact_email": self.contact_email,
            "invoice_title": self.invoice_title,
            "tax_id": self.tax_id,
            "invoice_address": self.invoice_address,
            "invoice_phone": self.invoice_phone,
            "invoice_bank_name": self.invoice_bank_name,
            "invoice_bank_account": self.invoice_bank_account,
            "invoice_email": self.invoice_email,
            "created_at": self.created_at or now_iso(),
            "updated_at": self.updated_at or now_iso(),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Tenant:
        return cls(
            id=str(raw.get("tenant_id") or raw.get("id") or ""),
            name=str(raw.get("name") or ""),
            status=str(raw.get("status") or "active"),
            contact_name=str(raw.get("contact_name") or ""),
            contact_phone=str(raw.get("contact_phone") or ""),
            contact_email=str(raw.get("contact_email") or ""),
            invoice_title=str(raw.get("invoice_title") or ""),
            tax_id=str(raw.get("tax_id") or ""),
            invoice_address=str(raw.get("invoice_address") or ""),
            invoice_phone=str(raw.get("invoice_phone") or ""),
            invoice_bank_name=str(raw.get("invoice_bank_name") or ""),
            invoice_bank_account=str(raw.get("invoice_bank_account") or ""),
            invoice_email=str(raw.get("invoice_email") or ""),
            created_at=str(raw.get("created_at") or ""),
            updated_at=str(raw.get("updated_at") or ""),
        )


@dataclass(slots=True)
class VerificationCode:
    id: str
    phone: str
    purpose: str
    code_hash: str
    expires_at: str
    created_at: str
    attempts: int = 0
    used: bool = False
    client_ip: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "phone": self.phone,
            "purpose": self.purpose,
            "code_hash": self.code_hash,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "attempts": self.attempts,
            "used": self.used,
            "client_ip": self.client_ip,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> VerificationCode:
        return cls(
            id=str(raw.get("id") or ""),
            phone=str(raw.get("phone") or ""),
            purpose=str(raw.get("purpose") or ""),
            code_hash=str(raw.get("code_hash") or ""),
            expires_at=str(raw.get("expires_at") or ""),
            created_at=str(raw.get("created_at") or ""),
            attempts=int(raw.get("attempts") or 0),
            used=bool(raw.get("used", False)),
            client_ip=str(raw.get("client_ip") or ""),
        )


@dataclass(slots=True)
class LoginAttempt:
    id: str
    identifier: str
    client_ip: str
    ok: bool
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "identifier": self.identifier,
            "client_ip": self.client_ip,
            "ok": self.ok,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> LoginAttempt:
        return cls(
            id=str(raw.get("id") or ""),
            identifier=str(raw.get("identifier") or ""),
            client_ip=str(raw.get("client_ip") or ""),
            ok=bool(raw.get("ok", False)),
            created_at=str(raw.get("created_at") or ""),
        )
