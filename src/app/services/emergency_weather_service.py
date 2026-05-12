from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.core.models import Channel
from app.modules.integration.weather_provider import WeatherInfo, WeatherProvider
from app.modules.notification.models import NotificationTask
from app.modules.notification.service import NotificationService
from app.modules.trigger.risk_alert_service import RiskAlertService, RiskSignal
from app.services.template_service import TemplateService
from app.services.weather_alert_ai_service import WeatherAlertAIService

UTC = UTC


def _status_label(status: str) -> str:
    mapping = {
        "planned": "计划中",
        "in_progress": "进行中",
        "completed": "已完成",
        "cancelled": "已取消",
    }
    return mapping.get(status, status or "未知")


def _risk_label(level: str) -> str:
    mapping = {
        "critical": "高危",
        "high": "较高",
        "medium": "中等",
        "low": "关注",
    }
    return mapping.get(level, "关注")


def _risk_badge(level: str) -> str:
    mapping = {
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "low": "low",
    }
    return mapping.get(level, "medium")


def _forecast_text(weather: WeatherInfo) -> str:
    if not weather.daily_forecast:
        return ""
    parts: list[str] = []
    for item in weather.daily_forecast[:2]:
        fx_date = str(item.get("fx_date") or "").strip()
        text_day = str(item.get("text_day") or "").strip() or "天气变化"
        temp_min = item.get("temp_min")
        temp_max = item.get("temp_max")
        precip = item.get("precip")

        day_tokens = [fx_date + text_day if fx_date else text_day]
        if temp_min is not None and temp_max is not None:
            day_tokens.append(f"{temp_min:.0f}-{temp_max:.0f}°C")
        if precip is not None:
            day_tokens.append(f"降水{precip:.1f}mm")
        parts.append("，".join(day_tokens))
    return f"未来两天预报：{'；'.join(parts)}" if parts else ""


@dataclass(slots=True)
class EmergencyWeatherService:
    trip_repository: Any
    project_notification_config_repository: Any
    weather_provider: WeatherProvider
    risk_alert_service: RiskAlertService
    template_service: TemplateService
    notification_service: NotificationService
    ai_service: WeatherAlertAIService | None = None

    def _target_trips(self, tenant_id: str) -> list[dict[str, Any]]:
        trips = [
            item
            for item in self.trip_repository.list()
            if str(item.get("tenant_id") or "") == tenant_id
            and str(item.get("status") or "") in {"planned", "in_progress"}
        ]
        if trips:
            return trips[:3]
        fallback = [
            item
            for item in self.trip_repository.list()
            if str(item.get("tenant_id") or "") == tenant_id
        ]
        return fallback[:3]

    def _weather_for_trip(self, trip: dict[str, Any], tenant_id: str) -> WeatherInfo:
        project_id = str(trip.get("project_id") or trip.get("team_id") or trip.get("team") or "")
        project_config = self.project_notification_config_repository.get(
            project_id, tenant_id=tenant_id
        )
        weather_context = dict(project_config or {})
        weather_context.update(trip)
        return self.weather_provider.get_weather(
            str(trip.get("destination") or ""),
            location_context=weather_context,
        )

    def _build_signal(self, weather: WeatherInfo) -> RiskSignal:
        lowered_condition = weather.condition.lower()
        weather_code = "clear"
        if "rain" in lowered_condition or "雨" in weather.condition:
            weather_code = "rain"
        elif "snow" in lowered_condition or "雪" in weather.condition:
            weather_code = "snow"

        road_status = "normal"
        wind_scale = 5
        unresolved_minutes = 8
        if weather.warning_level in {"orange", "red"}:
            road_status = "closed"
            wind_scale = 8
            unresolved_minutes = 20
        elif weather.warning_level in {"yellow", "blue"} or weather_code in {"rain", "snow"}:
            road_status = "congested"
            wind_scale = 7 if weather_code == "rain" else 6
            unresolved_minutes = 10

        return RiskSignal(
            weather=weather_code,
            road_status=road_status,
            temperature=float(weather.temperature),
            wind_scale=wind_scale,
            unresolved_minutes=unresolved_minutes,
        )

    def get_summary(self, tenant_id: str) -> dict[str, Any]:
        trips = self._target_trips(tenant_id)
        if not trips:
            now = datetime.now(tz=UTC).isoformat()
            fallback_ai = {
                "ai_risk_analysis": {
                    "affected_trip_ids": [],
                    "affected_stage": "出发",
                    "recommend_send": False,
                    "summary": "AI 暂未识别到可评估的在途或即将出发旅行团，建议先补齐团期数据后再执行预警评估。",
                },
                "generated_copies": {
                    "tourist": "【出行提醒】当前暂无可发送的紧急天气通知对象。",
                    "internal": "【内部预警】暂无在途或待出发行程，不触发天气应急通知。",
                },
                "suggested_actions": ["完善团期数据后重试评估"],
            }
            return {
                "alert_id": "emergency-weather-empty",
                "title": "紧急天气通知",
                "risk_level": "high",
                "risk_level_label": "较高",
                "risk_level_badge": "high",
                "updated_at": now,
                "weather_summary": "当前暂无可联动的旅行团数据，请先导入行程后再生成天气预警通知。",
                "today_weather_summary": "暂无可评估天气数据",
                "affected_region": "暂无",
                "ai_risk_summary": fallback_ai["ai_risk_analysis"]["summary"],
                "affected_trip_count": 0,
                "affected_trips": [],
                "generated_notification": fallback_ai["generated_copies"]["tourist"],
                "tourist_notification": fallback_ai["generated_copies"]["tourist"],
                "internal_notification": fallback_ai["generated_copies"]["internal"],
                "ai_risk_analysis": fallback_ai["ai_risk_analysis"],
                "suggested_actions": fallback_ai["suggested_actions"],
                "channel": "sms",
                "requires_confirmation": True,
            }

        selected_trip = trips[0]
        weather = self._weather_for_trip(selected_trip, tenant_id)
        signal = self._build_signal(weather)
        risk_alert = self.risk_alert_service.evaluate(signal)
        risk_level = risk_alert.level if risk_alert is not None else "high"
        ai_summary_parts = []
        recommendation_actions: list[str] = []
        if risk_alert is not None:
            ai_summary_parts.append(
                "AI判断本次天气事件已触发"
                f"{len(risk_alert.hit_rules)}项风险规则，"
                f"当前建议按{_risk_label(risk_level)}等级处理。"
            )
            if risk_alert.recommendation_actions:
                recommendation_actions = risk_alert.recommendation_actions[:]
                ai_summary_parts.append("；".join(risk_alert.recommendation_actions[:3]))
        else:
            ai_summary_parts.append("AI判断存在潜在天气扰动，建议人工确认后提前触达受影响游客。")
            recommendation_actions = ["建议人工确认后发送通知", "建议领队检查集合点与交通替代方案"]

        affected_trips: list[dict[str, Any]] = []
        for trip in trips:
            summary = (
                f"{trip.get('destination', '')}，{trip.get('start_date', '')}出发，"
                f"{int(trip.get('participants', 0) or 0)}人，当前{_status_label(str(trip.get('status') or ''))}"
            )
            affected_trips.append(
                {
                    "trip_id": str(trip.get("id") or ""),
                    "team_id": str(trip.get("team_id") or trip.get("team") or ""),
                    "destination": str(trip.get("destination") or ""),
                    "status": str(trip.get("status") or ""),
                    "status_label": _status_label(str(trip.get("status") or "")),
                    "traveler_count": int(trip.get("participants", 0) or 0),
                    "summary": summary,
                }
            )

        weather_tokens = [
            weather.destination or str(selected_trip.get("destination") or ""),
            f"当前{weather.condition or '天气波动'}",
            f"{weather.temperature:.1f}°C",
        ]
        if weather.alert_title:
            weather_tokens.append(weather.alert_title)
        elif weather.warning_level:
            weather_tokens.append(f"{weather.warning_level}级预警")
        forecast_summary = _forecast_text(weather)
        if forecast_summary:
            weather_tokens.append(forecast_summary)

        generated_notification = (
            f"【紧急天气通知】{weather.destination or selected_trip.get('destination', '')}未来6小时"
            f"{weather.condition or '天气变化明显'}，当前气温{weather.temperature:.1f}°C。"
            f"{forecast_summary + '。' if forecast_summary else ''}"
            f"AI评估为{_risk_label(risk_level)}风险，预计影响{len(affected_trips)}个旅行团。"
            "请游客随身携带雨具和保暖衣物，减少长时间户外停留，集合与行程调整请以领队通知为准。"
        )
        ai_service = self.ai_service or WeatherAlertAIService()
        ai_generated = ai_service.generate(
            weather_summary="，".join([token for token in weather_tokens if token]),
            risk_level_label=_risk_label(risk_level),
            affected_region=weather.destination
            or str(selected_trip.get("destination") or "未知区域"),
            affected_trips=affected_trips,
            recommendation_actions=recommendation_actions,
        )

        return {
            "alert_id": f"emergency-weather-{selected_trip.get('id', 'default')}",
            "title": weather.alert_title or "紧急天气通知",
            "risk_level": risk_level,
            "risk_level_label": _risk_label(risk_level),
            "risk_level_badge": _risk_badge(risk_level),
            "updated_at": datetime.now(tz=UTC).isoformat(),
            "weather_summary": "，".join([token for token in weather_tokens if token]),
            "today_weather_summary": "，".join([token for token in weather_tokens if token]),
            "affected_region": weather.destination
            or str(selected_trip.get("destination") or "未知区域"),
            "ai_risk_summary": " ".join(ai_summary_parts),
            "affected_trip_count": len(affected_trips),
            "affected_trips": affected_trips,
            "generated_notification": ai_generated["generated_copies"]["tourist"]
            or generated_notification,
            "tourist_notification": ai_generated["generated_copies"]["tourist"],
            "internal_notification": ai_generated["generated_copies"]["internal"],
            "ai_risk_analysis": ai_generated["ai_risk_analysis"],
            "suggested_actions": ai_generated["suggested_actions"],
            "channel": "sms",
            "requires_confirmation": True,
        }

    def send_summary(
        self,
        *,
        tenant_id: str,
        operator_id: str,
        custom_content: str | None,
        channel: str,
    ) -> dict[str, Any]:
        summary = self.get_summary(tenant_id)
        content = (custom_content or summary["generated_notification"]).strip()
        first_trip = summary["affected_trips"][0] if summary["affected_trips"] else {}
        task = NotificationTask(
            tenant_id=tenant_id,
            team_id=str(first_trip.get("team_id") or ""),
            trip_id=str(first_trip.get("trip_id") or summary["alert_id"]),
            customer_id=operator_id,
            rendered_content=content,
            idempotency_key=f"emergency:{summary['alert_id']}:{datetime.now(tz=UTC).isoformat()}",
            primary_channel=Channel.SMS if channel == "sms" else Channel.WECHAT_WORK_GROUP,
            fallback_channel=Channel.WECHAT_WORK_GROUP,
            provider_context={
                "trip_label": str(first_trip.get("destination") or summary["title"]),
                "customer_name": "值班管家",
            },
        )
        result = self.notification_service.dispatch(task)
        return {
            "ok": bool(result.get("ok")),
            "status": task.status.value,
            "notification_id": task.id,
            "sent_count": max(summary["affected_trip_count"], 1),
            "content": content,
        }
