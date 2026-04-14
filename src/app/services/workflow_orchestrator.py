from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app.modules.integration.persistence import TripRepository
from app.modules.notification.models import NotificationTask
from app.modules.notification.service import NotificationService
from app.services.template_service import TemplateService

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    def __init__(
        self,
        trip_repository: TripRepository,
        template_service: TemplateService,
        notification_service: NotificationService,
    ) -> None:
        self.trip_repo = trip_repository
        self.tpl_service = template_service
        self.notif_service = notification_service

    def _get_season_template_code(self, base_prefix: str) -> str:
        """根据月份判断季节后缀"""
        month = date.today().month
        if 3 <= month <= 5:
            return f"{base_prefix}-spring"
        elif 6 <= month <= 8:
            return f"{base_prefix}-summer"
        elif 9 <= month <= 11:
            return f"{base_prefix}-autumn"
        else:
            return f"{base_prefix}-winter"

    def scan_and_trigger(self, tenant_id: str = "tenant-a") -> dict[str, Any]:
        """扫描所有行程并触发当日应发的通知"""
        today = date.today()
        trips = self.trip_repo.list()
        triggered_count = 0
        logs = []

        for trip in trips:
            if trip.get("tenant_id") != tenant_id:
                continue

            # 解析日期
            start_date = date.fromisoformat(str(trip["start_date"]))
            end_date = date.fromisoformat(str(trip["end_date"]))
            days_until_start = (start_date - today).days
            status = trip.get("status")

            # --- 场景 1: 行前准备 (T-3) ---
            if days_until_start == 3 and status == "planned":
                self._send(trip, "tpl-pre-3d", "T-3行程确认")
                triggered_count += 1
                logs.append(f"Trip {trip['id']}: Sent T-3 notice")

            # --- 场景 2: 出发前一天 (T-1) ---
            elif days_until_start == 1 and status == "planned":
                # 连发两条：欢迎词 + 乘机提示
                self._send(trip, "tpl-pre-1d-welcome", "T-1入群欢迎")
                self._send(trip, "tpl-pre-1d-tips", "T-1安检提示")
                triggered_count += 2
                logs.append(f"Trip {trip['id']}: Sent T-1 bundle")

            # --- 场景 3: 行中每日提示 ---
            elif status == "in_progress" or (start_date <= today <= end_date):
                # 落地首日特殊提示
                if today == start_date:
                    self._send(trip, "tpl-arrival-urumqi", "落地首日指引")
                    triggered_count += 1

                # 每日晨间提示 (自动判断季节)
                morning_tpl = self._get_season_template_code("tpl-morning")
                self._send(trip, morning_tpl, "行中晨间提示")
                triggered_count += 1
                logs.append(f"Trip {trip['id']}: Sent daily morning tips")

            # --- 场景 4: 下团欢送 (完结日) ---
            elif today == end_date:
                self._send(trip, "tpl-post-farewell", "下团欢送")
                triggered_count += 1
                logs.append(f"Trip {trip['id']}: Sent farewell")

        return {"status": "completed", "triggered_total": triggered_count, "details": logs}

    def _send(self, trip: dict, template_code: str, scene_label: str) -> None:
        """内部辅助：查找模板、渲染并发送"""
        try:
            # 1. 查找模板
            templates = self.tpl_service.list_notification_templates()
            template = next((t for t in templates if t.id == template_code), None)
            if not template:
                logger.warning(f"Template {template_code} not found, skipping {scene_label}")
                return

            # 2. 准备变量 (对接沙笛业务字段)
            variables = {
                "customer_name": "贵宾",  # 实际应从 Trip/Customer 关联中获取
                "destination": trip.get("destination", "新疆"),
                "flight_info": "请核对您的机票行程单",
                "climate": "昼夜温差大",
                "dress_code": "建议叠穿外套",
                "trip_date": str(trip.get("start_date")),
            }

            # 3. 渲染
            content = self.tpl_service.render_notification(template, variables)

            # 4. 创建任务
            task = NotificationTask(
                tenant_id=trip.get("tenant_id", "tenant-a"),
                team_id=str(trip.get("team_id") or ""),
                trip_id=str(trip.get("id")),
                customer_id="system-auto",
                rendered_content=content,
                idempotency_key=f"auto:{trip['id']}:{template_code}:{date.today()}",
                primary_channel=template.channel,
            )

            # 5. 发送
            self.notif_service.dispatch(task)
            logger.info(f"Auto-triggered {scene_label} for trip {trip['id']}")
        except Exception as e:
            logger.error(f"Failed to trigger {scene_label}: {str(e)}")
