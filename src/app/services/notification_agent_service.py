from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.services.llm_service import generate_smart_message


def _clean(value: str) -> str:
    return str(value or "").strip()


@dataclass(slots=True)
class AlgorithmAgent:
    """规则匹配与通知规划 Agent。"""

    def resolve_stage(self, *, travel_date: str, start_date: str, end_date: str) -> str:
        try:
            today = datetime.fromisoformat(travel_date).date()
            start = datetime.fromisoformat(start_date).date()
            end = datetime.fromisoformat(end_date).date()
        except ValueError:
            return "行程中"

        if today < start:
            return "行程前"
        if today == end:
            return "下团即付"
        if start <= today <= end:
            return "行程中"
        return "下团后短期"

    def select_time_node(self, stage: str) -> str:
        mapping = {
            "行程前": "出发前1天",
            "行程中": "每日固定时段",
            "下团即付": "下团即付",
            "下团后短期": "下团后短期",
        }
        return mapping.get(stage, "每日固定时段")

    def build_plan(
        self,
        *,
        stage: str,
        time_node: str,
        core_work: str,
        route_text: str,
        hotel: str,
        weather: str,
        special_tags: list[str],
    ) -> dict[str, Any]:
        special_text = "、".join([item for item in special_tags if item]) or "无"
        common_points = [
            f"今日路线：{route_text}",
            f"当前阶段：{stage}（{time_node}）",
            f"核心工作：{core_work}",
            f"天气：{weather}",
            f"入住信息：{hotel or '按领队通知'}",
        ]
        if special_text != "无":
            common_points.append(f"特殊场景：{special_text}")
        return {
            "morning": {
                "purpose": "早间出发与安全提示",
                "priority_points": ["集合时间", "今日路线", "安全提醒"],
                "content_points": common_points
                + ["请检查证件与随身物品", "出发前确认座位与安全带"],
                "max_length": 220,
            },
            "noon": {
                "purpose": "午间节奏与健康提示",
                "priority_points": ["天气变化", "补水与饮食", "财物安全"],
                "content_points": common_points + ["合理安排午间休息", "高风险场景执行专项提醒"],
                "max_length": 220,
            },
            "evening": {
                "purpose": "晚间复盘与次日预告",
                "priority_points": ["次日安排", "酒店入住", "退房集合提醒"],
                "content_points": common_points + ["复盘当日注意事项", "同步次日天气与出发时间"],
                "max_length": 240,
            },
        }


@dataclass(slots=True)
class WriterAgent:
    """LLM 文案生成 Agent。"""

    def _scene_prompt(self, period: str, plan: dict[str, Any], context: dict[str, Any]) -> str:
        points = "；".join(plan.get("content_points", []))
        priority = "；".join(plan.get("priority_points", []))
        return (
            "你是旅行社通知文案助手，请写给游客群的中文通知。"
            f"发送时段：{period}；目的：{plan.get('purpose', '')}。"
            f"必须覆盖重点：{priority}。"
            f"参考信息：{points}。"
            f"团名：{context.get('group_name', '')}；路线：{context.get('route_text', '')}；"
            f"酒店：{context.get('hotel', '')}；天气：{context.get('weather', '')}。"
            "要求：语气专业温暖，120-220字，不要编造。"
        )

    def generate_message(
        self, *, period: str, plan: dict[str, Any], context: dict[str, Any]
    ) -> str:
        scene = f"{period}通知"
        prompt = self._scene_prompt(period, plan, context)
        try:
            return asyncio.run(
                generate_smart_message(
                    trip_destination=context.get("route_text", ""),
                    scene=scene,
                    prompt_override=prompt,
                )
            )
        except RuntimeError:
            return self._fallback_message(period=period, plan=plan, context=context)

    def _fallback_message(
        self, *, period: str, plan: dict[str, Any], context: dict[str, Any]
    ) -> str:
        line1 = (
            f"【{period}提醒】{context.get('group_name', '各位团友')}，{plan.get('purpose', '')}。"
        )
        line2 = f"今日路线：{context.get('route_text', '')}；天气：{context.get('weather', '')}。"
        line3 = "；".join(plan.get("priority_points", []))
        return f"{line1}{line2}请重点关注：{line3}。"


@dataclass(slots=True)
class ValidatorAgent:
    """通知校验 Agent，确保关键点不遗漏。"""

    def validate(self, *, message: str, priority_points: list[str]) -> tuple[str, list[str]]:
        missing = [point for point in priority_points if point and point not in message]
        if not missing:
            return message, []
        suffix = "；".join([f"请关注{item}" for item in missing])
        return f"{message} {suffix}。", missing


@dataclass(slots=True)
class NotificationAgentService:
    """主控 Agent：编排规则、LLM、校验并产出早中晚通知。"""

    algorithm_agent: AlgorithmAgent = field(default_factory=AlgorithmAgent)
    writer_agent: WriterAgent = field(default_factory=WriterAgent)
    validator_agent: ValidatorAgent = field(default_factory=ValidatorAgent)

    def generate_daily_drafts(
        self,
        *,
        route: str,
        travel_stage: str,
        time_node: str,
        core_work: str,
        action_detail: str = "",
    ) -> dict[str, Any]:
        route_text = _clean(route) or "当前路线"
        stage_text = _clean(travel_stage) or "行程中"
        node_text = _clean(time_node) or "每日固定时段"
        work_text = _clean(core_work) or "行程服务保障"
        detail_text = _clean(action_detail)

        context_line = f"路线：{route_text}；阶段：{stage_text}；时间节点：{node_text}；核心工作：{work_text}。"
        if detail_text:
            context_line = f"{context_line}重点动作：{detail_text}"

        morning = (
            f"【早安提醒】{route_text}今日行程开始，请大家按约定时间集合并检查证件与随身物品。"
            f"{work_text}是今天首要任务，请优先确认车次、座位与安全带佩戴。"
        )
        noon = (
            f"【午间提醒】当前处于{stage_text}，请根据现场天气与路况灵活调整节奏。"
            f"围绕“{work_text}”持续跟进，用餐后及时清点人员并同步下一段集合点。"
        )
        evening = (
            f"【晚间播报】{route_text}今日执行完成，请复盘{work_text}并发布次日出发时间。"
            "请提醒游客今晚尽早休息，明日行程及天气变化以群内通知为准。"
        )

        return {
            "context": {
                "route": route_text,
                "travel_stage": stage_text,
                "time_node": node_text,
                "core_work": work_text,
                "action_detail": detail_text,
                "prompt_summary": context_line,
            },
            "drafts": [
                {"time_slot": "morning", "title": "早间提示", "content": morning},
                {"time_slot": "noon", "title": "午间提示", "content": noon},
                {"time_slot": "evening", "title": "晚间提示", "content": evening},
            ],
        }

    def generate_daily_messages(
        self,
        *,
        group_id: str,
        group_name: str,
        travel_date: str,
        start_date: str,
        end_date: str,
        route_text: str,
        hotel: str,
        weather: str,
        core_work: str,
        special_tags: list[str],
    ) -> dict[str, Any]:
        stage = self.algorithm_agent.resolve_stage(
            travel_date=travel_date,
            start_date=start_date,
            end_date=end_date,
        )
        time_node = self.algorithm_agent.select_time_node(stage)
        plan = self.algorithm_agent.build_plan(
            stage=stage,
            time_node=time_node,
            core_work=core_work or "时段性专属温馨提示",
            route_text=route_text,
            hotel=hotel,
            weather=weather,
            special_tags=special_tags,
        )

        context = {
            "group_id": group_id,
            "group_name": group_name,
            "date": travel_date,
            "route_text": route_text,
            "hotel": hotel,
            "weather": weather,
        }
        messages: list[dict[str, Any]] = []
        debug: dict[str, Any] = {
            "stage": stage,
            "time_node": time_node,
            "route_text": route_text,
            "plan": plan,
            "validation": {},
        }
        for period in ("morning", "noon", "evening"):
            period_plan = plan[period]
            generated = self.writer_agent.generate_message(
                period=period, plan=period_plan, context=context
            )
            validated, missing = self.validator_agent.validate(
                message=generated,
                priority_points=period_plan.get("priority_points", []),
            )
            title_map = {
                "morning": "今日出发提醒",
                "noon": "午间温馨提醒",
                "evening": "今晚入住与明日预告",
            }
            messages.append(
                {
                    "period": period,
                    "title": title_map[period],
                    "message": validated,
                    "short_version": validated[:80],
                    "key_points": period_plan.get("priority_points", []),
                }
            )
            debug["validation"][period] = {"missing_points": missing}
        return {
            "group_id": group_id,
            "date": travel_date,
            "stage": stage,
            "time_node": time_node,
            "messages": messages,
            "debug": debug,
        }
