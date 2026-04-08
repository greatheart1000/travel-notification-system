from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.core.models import Channel, NotificationType
from app.modules.notification.models import NotificationTemplate
from app.modules.trigger.models import TriggerRule


class JourneyStage(str, Enum):
    PRE_TRIP = "pre_trip"
    ON_TRIP = "on_trip"
    POST_TRIP = "post_trip"


@dataclass(slots=True)
class LifecycleRuleDraft:
    """Structured rule draft generated from travel operation table."""

    code: str
    stage: JourneyStage
    time_node: str
    core_work: str
    actions: list[str] = field(default_factory=list)
    notification_type: NotificationType = NotificationType.DAILY_REMINDER
    is_mandatory: bool = True
    source: str = "system_schedule"
    priority: int = 100
    conditions: dict[str, object] = field(default_factory=dict)


class LifecycleRuleBuilder:
    """Builds stage-based trigger rules and templates for full trip lifecycle."""

    def build_default_drafts(self) -> list[LifecycleRuleDraft]:
        return [
            LifecycleRuleDraft(
                code="pre_t_minus_3_customer_check",
                stage=JourneyStage.PRE_TRIP,
                time_node="出发前3天",
                core_work="游客沟通+行程单处理",
                actions=[
                    "联系游客确认航班、证件、天气、着装、饮食禁忌注意事项",
                    "打印并发送含导游信息的行程单",
                    "完成电子版行程单留档",
                ],
                notification_type=NotificationType.PRE_TRIP_REMINDER,
                priority=10,
            ),
            LifecycleRuleDraft(
                code="pre_departure_resource_check",
                stage=JourneyStage.PRE_TRIP,
                time_node="出发前",
                core_work="资源与物资确认",
                actions=[
                    "确认酒店、用车、司机、游客匹配完成",
                    "核查无人机、户外桌椅、物资筹备状态",
                ],
                notification_type=NotificationType.PRE_TRIP_REMINDER,
                priority=20,
            ),
            LifecycleRuleDraft(
                code="pre_t_minus_1_risk_and_handover",
                stage=JourneyStage.PRE_TRIP,
                time_node="出发前1天",
                core_work="保险检查+群聊搭建+司导交底",
                actions=[
                    "检查保险购买完成度",
                    "发送出发联系通知并建立游客服务群",
                    "与司机确认并交接行程及评分标准",
                    "发送群欢迎语并完成司机/导游自我介绍",
                ],
                notification_type=NotificationType.RISK_ALERT,
                priority=30,
            ),
            LifecycleRuleDraft(
                code="on_arrival_local_guide",
                stage=JourneyStage.ON_TRIP,
                time_node="游客落地乌鲁木齐当日",
                core_work="本地指引+通用提示",
                actions=[
                    "推送特色景点与美食推荐",
                    "发送当日天气与衣物提示",
                    "同步交通、安保、计量单位、网络等实用信息",
                ],
                notification_type=NotificationType.DAILY_REMINDER,
                priority=40,
            ),
            LifecycleRuleDraft(
                code="on_daily_timed_notice",
                stage=JourneyStage.ON_TRIP,
                time_node="每日固定时段",
                core_work="时段性专属温馨提示",
                actions=[
                    "早间发送展望提醒与行李建议",
                    "中午发送防晒、防雨、防骗提示",
                    "晚间发送次日天气和行程简报",
                ],
                notification_type=NotificationType.DAILY_REMINDER,
                priority=50,
                conditions={"time_window": {"op": "in", "value": ["morning", "noon", "evening"]}},
            ),
            LifecycleRuleDraft(
                code="on_special_scene_safety",
                stage=JourneyStage.ON_TRIP,
                time_node="特殊游玩场景",
                core_work="专项安全提示",
                actions=[
                    "按骑马等项目发布核心安全提示",
                    "针对高原、边境口岸、极寒、强紫外线区域发送专属提醒",
                ],
                notification_type=NotificationType.RISK_ALERT,
                source="weather_and_scene_tags",
                priority=60,
                conditions={"scene_level": {"op": "in", "value": ["highland", "border", "extreme_weather"]}},
            ),
            LifecycleRuleDraft(
                code="on_trip_triage_collab",
                stage=JourneyStage.ON_TRIP,
                time_node="全程",
                core_work="三方协调沟通",
                actions=["实时协同游客、导游、旅行社三方问题并闭环"],
                notification_type=NotificationType.DAILY_REMINDER,
                priority=70,
            ),
            LifecycleRuleDraft(
                code="post_immediate_farewell_and_survey",
                stage=JourneyStage.POST_TRIP,
                time_node="下团即时",
                core_work="欢送+满意度调研",
                actions=[
                    "发送二次欢迎类关怀消息",
                    "发起客户满意度调查并同步结果给客服与销售",
                ],
                notification_type=NotificationType.SATISFACTION,
                priority=80,
            ),
            LifecycleRuleDraft(
                code="post_short_term_followup_archive",
                stage=JourneyStage.POST_TRIP,
                time_node="下团后短期内",
                core_work="售后跟进+客户存档",
                actions=[
                    "执行售后跟进并沉淀全流程服务记录",
                    "高品质游客信息专项存档并反馈销售",
                ],
                notification_type=NotificationType.SATISFACTION,
                priority=90,
            ),
            LifecycleRuleDraft(
                code="post_late_group_close",
                stage=JourneyStage.POST_TRIP,
                time_node="售后末期",
                core_work="群聊解散",
                actions=["发送群解散通知与祝福并正式结束服务群"],
                notification_type=NotificationType.FAREWELL,
                priority=100,
            ),
        ]

    def to_trigger_rules(self, drafts: list[LifecycleRuleDraft]) -> list[TriggerRule]:
        return [
            TriggerRule(
                code=draft.code,
                name=f"{draft.stage.value}:{draft.core_work}",
                notification_type=draft.notification_type,
                is_mandatory=draft.is_mandatory,
                source=draft.source,
                priority=draft.priority,
                conditions=draft.conditions,
            )
            for draft in drafts
        ]

    def to_notification_templates(
        self,
        drafts: list[LifecycleRuleDraft],
        channel: Channel = Channel.WECHAT_WORK_GROUP,
    ) -> list[NotificationTemplate]:
        templates: list[NotificationTemplate] = []
        for draft in drafts:
            action_text = "；".join(draft.actions)
            templates.append(
                NotificationTemplate(
                    name=f"{draft.code}_v1",
                    notification_type=draft.notification_type,
                    channel=channel,
                    content=f"[{draft.time_node}] {draft.core_work}：{action_text}",
                )
            )
        return templates
