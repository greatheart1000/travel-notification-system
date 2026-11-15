from __future__ import annotations

import pytest

from app.core.models import Channel
from app.services.template_service import TemplateService


def _service() -> TemplateService:
    return TemplateService()


def test_render_notification_supports_whitespace_and_repeated_placeholders() -> None:
    template = _service().create_notification_template(
        tenant_id="tenant-a",
        name="render",
        content="你好 {{ customer_name }}，{{customer_name}} 欢迎来 {{ destination }}。",
        channel="sms",
        notification_type="daily_reminder",
        is_active=True,
    )

    rendered = _service().render_notification(
        template, {"customer_name": "张三", "destination": "新疆"}
    )

    assert rendered == "你好 张三，张三 欢迎来 新疆。"


def test_render_notification_reports_missing_fields() -> None:
    template = _service().create_notification_template(
        tenant_id="tenant-a",
        name="missing",
        content="{{ customer_name }} / {{ destination }}",
        channel="sms",
        notification_type="daily_reminder",
        is_active=True,
    )

    with pytest.raises(ValueError) as exc:
        _service().render_notification(template, {"customer_name": "张三"})

    assert "destination" in str(exc.value)


def test_pick_notification_template_prefers_exact_project_match() -> None:
    service = _service()
    service.create_notification_template(
        tenant_id="tenant-a",
        name="generic",
        content="generic",
        channel="sms",
        notification_type="daily_reminder",
        is_active=True,
        stage="in_trip",
        time_slot="morning",
        scene="normal",
    )
    exact = service.create_notification_template(
        tenant_id="tenant-a",
        name="exact",
        content="exact",
        channel="sms",
        notification_type="daily_reminder",
        is_active=True,
        project_id="proj-1",
        stage="in_trip",
        time_slot="morning",
        scene="normal",
    )

    picked = service.pick_notification_template(
        tenant_id="tenant-a",
        project_id="proj-1",
        stage="in_trip",
        time_slot="morning",
        scene="normal",
        channel="sms",
    )

    assert picked is not None
    assert picked.id == exact.id


def test_pick_notification_template_isolates_tenants() -> None:
    service = _service()
    service.create_notification_template(
        tenant_id="tenant-a",
        name="a-only",
        content="a",
        channel="sms",
        notification_type="daily_reminder",
        is_active=True,
        stage="in_trip",
        time_slot="morning",
        scene="normal",
    )

    assert (
        service.pick_notification_template(
            tenant_id="tenant-b",
            project_id="proj-1",
            stage="in_trip",
            time_slot="morning",
            scene="normal",
            channel="sms",
        )
        is None
    )


def test_ensure_default_template_always_returns_sms_channel() -> None:
    service = _service()
    service.create_notification_template(
        tenant_id="tenant-a",
        name="wechat-only",
        content="wechat",
        channel="wechat_work_group",
        notification_type="daily_reminder",
        is_active=True,
    )

    template = service.ensure_default_template(tenant_id="tenant-a")

    assert template.channel is Channel.SMS


def test_template_crud_and_tenant_filters(json_store) -> None:
    service = TemplateService(store=json_store)
    created = service.create_notification_template(
        tenant_id="tenant-a",
        name="提醒",
        content="你好 {{customer_name}}",
        channel="短信",
        notification_type="daily_reminder",
        is_active=True,
        project_id="proj-1",
        stage="in_trip",
        time_slot="morning",
        scene="normal",
    )

    assert service.get_notification_template(created.id, tenant_id="tenant-a") is not None
    assert service.get_notification_template(created.id, tenant_id="tenant-b") is None
    assert len(service.list_notification_templates(tenant_id="tenant-a")) == 1
    assert service.list_notification_templates(tenant_id="tenant-b") == []

    updated = service.update_notification_template(
        created.id,
        name="新提醒",
        content="更新 {{customer_name}}",
        channel="wechat",
        is_active=False,
    )
    assert updated is not None
    assert updated.name == "新提醒"
    assert updated.channel is Channel.WECHAT_WORK_GROUP
    assert updated.is_active is False

    assert service.delete_notification_template(created.id) is True
    assert service.get_notification_template(created.id) is None
    assert service.delete_notification_template("missing") is False


def test_pick_notification_template_returns_none_when_no_match() -> None:
    service = _service()

    assert (
        service.pick_notification_template(
            tenant_id="tenant-a",
            project_id="proj-1",
            stage="in_trip",
            time_slot="morning",
            scene="normal",
            channel="sms",
        )
        is None
    )


def test_legacy_template_helpers_still_work() -> None:
    from app.core.entities import EventName
    from app.core.entities import Template as RuleTemplate

    service = _service()
    service.upsert_template(
        RuleTemplate(
            template_id="legacy-1",
            event_name=EventName.TRIP_CREATED,
            locale="zh",
            version=1,
            content="你好 {{name}}",
        )
    )

    picked = service.pick_template(EventName.TRIP_CREATED, "zh")
    rendered = service.render(picked, {"name": "张三"})

    assert picked.template_id == "legacy-1"
    assert rendered == "你好 张三"


def test_resolve_seasonal_template_switches_by_month() -> None:
    service = _service()
    spring = service.create_notification_template(
        tenant_id="tenant-a",
        name="晨间提示-春季",
        content="spring",
        channel="wechat_work_group",
        notification_type="daily_reminder",
        is_active=True,
    )
    autumn = service.create_notification_template(
        tenant_id="tenant-a",
        name="晨间提示-秋季",
        content="autumn",
        channel="wechat_work_group",
        notification_type="daily_reminder",
        is_active=True,
    )

    resolved = service.resolve_seasonal_template(spring, tenant_id="tenant-a", month=10)

    assert resolved is not None
    assert resolved.id == autumn.id
