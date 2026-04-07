from __future__ import annotations

from dataclasses import dataclass

from app.core.entities import Channel


@dataclass(slots=True)
class ProviderResult:
    ok: bool
    provider: str
    message: str


class BaseProvider:
    channel: Channel

    def send(self, user_id: str, content: str) -> ProviderResult:
        raise NotImplementedError


class EmailProvider(BaseProvider):
    channel = Channel.EMAIL

    def send(self, user_id: str, content: str) -> ProviderResult:
        return ProviderResult(ok=True, provider="email", message=f"email sent to {user_id}")


class PushProvider(BaseProvider):
    channel = Channel.PUSH

    def __init__(self, fail_first: bool = False) -> None:
        self.fail_first = fail_first
        self._has_failed = False

    def send(self, user_id: str, content: str) -> ProviderResult:
        if self.fail_first and not self._has_failed:
            self._has_failed = True
            return ProviderResult(ok=False, provider="push", message="temporary provider error")
        return ProviderResult(ok=True, provider="push", message=f"push sent to {user_id}")


class SmsProvider(BaseProvider):
    channel = Channel.SMS

    def send(self, user_id: str, content: str) -> ProviderResult:
        return ProviderResult(ok=True, provider="sms", message=f"sms sent to {user_id}")
