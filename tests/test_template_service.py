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
