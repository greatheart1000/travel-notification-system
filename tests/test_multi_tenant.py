from __future__ import annotations

from app.modules.integration.persistence import (
    ProjectNotificationConfigRepository,
    TripRepository,
)


def test_trip_repository_filters_by_tenant(json_store) -> None:
    repo = TripRepository(store=json_store)
    repo.create({"id": "trip-a", "tenant_id": "tenant-a", "destination": "A"})
    repo.create({"id": "trip-b", "tenant_id": "tenant-b", "destination": "B"})

    assert [item["id"] for item in repo.list(tenant_id="tenant-a")] == ["trip-a"]
    assert [item["id"] for item in repo.list(tenant_id="tenant-b")] == ["trip-b"]
    assert repo.get("trip-b", tenant_id="tenant-a") is None
    assert repo.get("trip-b", tenant_id="tenant-b")["destination"] == "B"


def test_project_config_upsert_is_tenant_scoped(json_store) -> None:
    repo = ProjectNotificationConfigRepository(store=json_store)
    repo.upsert({"tenant_id": "tenant-a", "project_id": "proj-1", "project_name": "A"})
    repo.upsert({"tenant_id": "tenant-b", "project_id": "proj-1", "project_name": "B"})

    assert repo.get("proj-1", tenant_id="tenant-a")["project_name"] == "A"
    assert repo.get("proj-1", tenant_id="tenant-b")["project_name"] == "B"


def test_project_config_list_never_returns_other_tenants(json_store) -> None:
    repo = ProjectNotificationConfigRepository(store=json_store)
    repo.upsert({"tenant_id": "tenant-a", "project_id": "proj-1", "project_name": "A"})

    assert repo.list(tenant_id="tenant-b") == []
