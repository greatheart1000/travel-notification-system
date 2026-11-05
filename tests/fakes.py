from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.models import Channel
from app.modules.integration.sms_provider import SMSProvider
from app.modules.integration.weather_provider import WeatherInfo


@dataclass
class FakeChannelProvider:
    """Records sends and returns scripted outcomes."""

    outcomes: list[tuple[bool, str]] = field(default_factory=list)
    default: tuple[bool, str] = (True, "ok")
    calls: list[dict[str, Any]] = field(default_factory=list)

    def send(
        self,
        customer_id: str,
        content: str,
        provider_context: dict[str, str] | None = None,
    ) -> tuple[bool, str]:
        self.calls.append(
            {
                "customer_id": customer_id,
                "content": content,
                "provider_context": dict(provider_context or {}),
            }
        )
        if self.outcomes:
            return self.outcomes.pop(0)
        return self.default

    @property
    def call_count(self) -> int:
        return len(self.calls)


@dataclass
class FakeSMSProvider(SMSProvider):
    outcomes: list[dict[str, Any]] = field(default_factory=list)
    default: dict[str, Any] = field(default_factory=lambda: {"ok": True, "msg_id": "fake-sms"})
    calls: list[dict[str, Any]] = field(default_factory=list)

    def send_sms(
        self,
        phone: str,
        content: str,
        sign_name: str = "TravelHub",
        template_code: str = "",
        template_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "phone": phone,
                "content": content,
                "sign_name": sign_name,
                "template_code": template_code,
                "template_params": template_params,
            }
        )
        if self.outcomes:
            return self.outcomes.pop(0)
        return dict(self.default)


@dataclass
class FakeWeatherProvider:
    weather: WeatherInfo = field(
        default_factory=lambda: WeatherInfo(
            destination="测试目的地",
            condition="晴",
            temperature=20.0,
            source="fake",
        )
    )
    error: Exception | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    def get_weather(
        self,
        destination: str,
        location_context: dict[str, Any] | None = None,
    ) -> WeatherInfo:
        self.calls.append(
            {"destination": destination, "location_context": dict(location_context or {})}
        )
        if self.error is not None:
            raise self.error
        return self.weather


@dataclass
class RecordingAudit:
    logs: list[dict[str, Any]] = field(default_factory=list)

    def record(
        self,
        operator_id: str,
        action: str,
        target: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.logs.append(
            {
                "operator_id": operator_id,
                "action": action,
                "target": target,
                "detail": detail or {},
            }
        )


def fake_providers(
    *,
    sms: FakeChannelProvider | None = None,
    wechat: FakeChannelProvider | None = None,
) -> dict[Channel, FakeChannelProvider]:
    return {
        Channel.SMS: sms or FakeChannelProvider(),
        Channel.WECHAT_WORK_GROUP: wechat or FakeChannelProvider(),
    }
