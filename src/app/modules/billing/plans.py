from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Plan:
    """A subscription plan sold to a tenant."""

    code: str
    name: str
    price_cents: int
    sms_quota: int
    period_days: int = 30
    features: tuple[str, ...] = field(default_factory=tuple)
    sort_order: int = 0
    is_public: bool = True
    is_free: bool = False

    @property
    def price_yuan(self) -> str:
        return f"{self.price_cents / 100:.2f}"

    def to_public_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "name": self.name,
            "price_cents": self.price_cents,
            "price_yuan": self.price_yuan,
            "currency": os.getenv("BILLING_CURRENCY", "CNY"),
            "sms_quota": self.sms_quota,
            "period_days": self.period_days,
            "features": list(self.features),
            "is_free": self.is_free,
        }


DEFAULT_PLANS: tuple[Plan, ...] = (
    Plan(
        code="free",
        name="免费版",
        price_cents=0,
        sms_quota=20,
        features=("企业微信群通知", "1 个管理员账号", "20 条短信/月"),
        sort_order=0,
        is_free=True,
    ),
    Plan(
        code="starter",
        name="标准版",
        price_cents=29900,
        sms_quota=2000,
        features=("企业微信群通知", "短信通知", "5 个账号", "2,000 条短信/月", "工单支持"),
        sort_order=10,
    ),
    Plan(
        code="growth",
        name="成长版",
        price_cents=99900,
        sms_quota=10000,
        features=("全部标准版能力", "20 个账号", "10,000 条短信/月", "优先支持"),
        sort_order=20,
    ),
    Plan(
        code="enterprise",
        name="企业版",
        price_cents=299900,
        sms_quota=50000,
        features=("全部成长版能力", "不限账号数", "50,000 条短信/月", "专属客户成功"),
        sort_order=30,
    ),
    Plan(
        code="trial",
        name="试用版",
        price_cents=0,
        sms_quota=100,
        period_days=14,
        features=("14 天全功能试用", "100 条短信", "无需绑定支付方式"),
        sort_order=5,
        is_public=False,
        is_free=True,
    ),
)


def _apply_runtime_overrides(plans: list[Plan]) -> list[Plan]:
    import dataclasses

    overrides: dict[str, dict[str, int]] = {}
    try:
        trial_quota = int(os.getenv("BILLING_TRIAL_SMS_QUOTA", "100"))
        trial_days = int(os.getenv("BILLING_TRIAL_DAYS", "14"))
    except ValueError:
        trial_quota, trial_days = 100, 14
    overrides["trial"] = {
        "sms_quota": max(trial_quota, 0),
        "period_days": max(trial_days, 1),
    }
    result: list[Plan] = []
    for plan in plans:
        patch = overrides.get(plan.code)
        result.append(dataclasses.replace(plan, **patch) if patch else plan)
    return result


def _plan_from_dict(raw: dict[str, object], index: int) -> Plan:
    return Plan(
        code=str(raw["code"]),
        name=str(raw.get("name") or raw["code"]),
        price_cents=int(raw.get("price_cents") or 0),
        sms_quota=int(raw.get("sms_quota") or 0),
        period_days=int(raw.get("period_days") or 30),
        features=tuple(str(item) for item in (raw.get("features") or [])),
        sort_order=int(raw.get("sort_order") or index * 10),
        is_public=bool(raw.get("is_public", True)),
        is_free=bool(raw.get("is_free", False)),
    )


def load_plans() -> list[Plan]:
    """Return the plan catalog, optionally overridden by BILLING_PLANS_JSON."""
    raw = os.getenv("BILLING_PLANS_JSON", "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:  # pragma: no cover - config error path
            raise RuntimeError(f"BILLING_PLANS_JSON is not valid JSON: {exc}") from exc
        if not isinstance(parsed, list) or not parsed:
            raise RuntimeError("BILLING_PLANS_JSON must be a non-empty JSON array")
        return [_plan_from_dict(item, index) for index, item in enumerate(parsed)]
    return _apply_runtime_overrides(list(DEFAULT_PLANS))


def get_plan(code: str) -> Plan | None:
    for plan in load_plans():
        if plan.code == code:
            return plan
    return None


def require_plan(code: str) -> Plan:
    plan = get_plan(code)
    if plan is None:
        raise ValueError(f"unknown_plan:{code}")
    return plan
