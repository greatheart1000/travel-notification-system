from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.modules.integration.persistence import JsonFileStore

UTC = UTC

@dataclass(slots=True)
class TripRepository:
    store: JsonFileStore
    collection: str = "trips"

    def list(self) -> list[dict[str, Any]]:
        return self.store.read_collection(self.collection)

    def get(self, trip_id: str) -> dict[str, Any] | None:
        for item in self.list():
            if item.get("id") == trip_id:
                return item
        return None

    def create(self, trip: dict[str, Any]) -> dict[str, Any]:
        return self.store.upsert(self.collection, trip)

    def update(self, trip_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        current = self.get(trip_id)
        if current is None:
            return None
        current.update(patch)
        current["updated_at"] = datetime.utcnow().isoformat()
        self.store.upsert(self.collection, current)
        return current

    def delete(self, trip_id: str) -> bool:
        return self.store.delete(self.collection, trip_id)


@dataclass(slots=True)
class TripStaffRepository:
    """行程人员仓库（团期负责人/管家/司机）。"""
    store: JsonFileStore
    collection: str = "trip_staff"

    def get_by_trip(self, trip_id: str) -> list[dict[str, Any]]:
        rows = self.store.read_collection(self.collection)
        return [r for r in rows if str(r.get("trip_id")) == trip_id]

    def upsert(self, trip_id: str, role: str, name: str, phone: str) -> dict[str, Any]:
        rows = self.store.read_collection(self.collection)
        existing = next((r for r in rows if str(r.get("trip_id")) == trip_id and r.get("role") == role), None)
        item = {"trip_id": trip_id, "role": role, "name": name, "phone": phone}
        if existing:
            existing.update(item)
        else:
            item["id"] = f"staff-{trip_id}-{role}"
            rows.append(item)
        self.store.write_collection(self.collection, rows)
        return existing or item

    def put_staff_batch(self, trip_id: str, staff_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = self.store.read_collection(self.collection)
        rows = [r for r in rows if str(r.get("trip_id")) != trip_id]
        results = []
        for s in staff_list:
            item = {
                "id": f"staff-{trip_id}-{s.get('role','')}",
                "trip_id": trip_id,
                "role": s.get("role", ""),
                "name": s.get("name", ""),
                "phone": s.get("phone", ""),
            }
            rows.append(item)
            results.append(item)
        self.store.write_collection(self.collection, rows)
        return results


@dataclass(slots=True)
class GuestRepository:
    """游客仓库（独立实体）。"""
    store: JsonFileStore
    collection: str = "guests"

    def list(self, tenant_id: str = "tenant-a") -> list[dict[str, Any]]:
        return [r for r in self.store.read_collection(self.collection) if r.get("tenant_id") == tenant_id]

    def get(self, guest_id: str) -> dict[str, Any] | None:
        for r in self.store.read_collection(self.collection):
            if str(r.get("id")) == guest_id:
                return r
        return None

    def get_by_phone(self, phone: str, tenant_id: str = "tenant-a") -> dict[str, Any] | None:
        for r in self.store.read_collection(self.collection):
            if r.get("phone") == phone and r.get("tenant_id") == tenant_id:
                return r
        return None

    def create(self, item: dict[str, Any]) -> dict[str, Any]:
        import uuid
        item["id"] = str(item.get("id") or f"guest-{uuid.uuid4().hex[:10]}")
        item.setdefault("tenant_id", "tenant-a")
        item.setdefault("is_vip", False)
        rows = self.store.read_collection(self.collection)
        rows.append(item)
        self.store.write_collection(self.collection, rows)
        return item

    def update(self, guest_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        rows = self.store.read_collection(self.collection)
        for r in rows:
            if str(r.get("id")) == guest_id:
                r.update(patch)
                self.store.write_collection(self.collection, rows)
                return r
        return None

    def delete(self, guest_id: str) -> bool:
        rows = self.store.read_collection(self.collection)
        new_rows = [r for r in rows if str(r.get("id")) != guest_id]
        if len(new_rows) == len(rows):
            return False
        self.store.write_collection(self.collection, new_rows)
        return True


@dataclass(slots=True)
class TripGuestRepository:
    """行程-游客关联仓库。"""
    store: JsonFileStore
    collection: str = "trip_guests"

    def get_guest_ids(self, trip_id: str) -> list[str]:
        rows = self.store.read_collection(self.collection)
        return [str(r["guest_id"]) for r in rows if str(r.get("trip_id")) == trip_id]

    def get_trip_ids(self, guest_id: str) -> list[str]:
        rows = self.store.read_collection(self.collection)
        return [str(r["trip_id"]) for r in rows if str(r.get("guest_id")) == guest_id]

    def link(self, trip_id: str, guest_id: str) -> dict[str, Any]:
        rows = self.store.read_collection(self.collection)
        existing = next((r for r in rows if str(r.get("trip_id")) == trip_id and str(r.get("guest_id")) == guest_id), None)
        if existing:
            return existing
        item = {"id": f"tg-{trip_id}-{guest_id}", "trip_id": trip_id, "guest_id": guest_id}
        rows.append(item)
        self.store.write_collection(self.collection, rows)
        return item

    def unlink(self, trip_id: str, guest_id: str) -> bool:
        rows = self.store.read_collection(self.collection)
        new_rows = [r for r in rows if not (str(r.get("trip_id")) == trip_id and str(r.get("guest_id")) == guest_id)]
        if len(new_rows) == len(rows):
            return False
        self.store.write_collection(self.collection, new_rows)
        return True


@dataclass(slots=True)
class TripItineraryRepository:
    """每日行程表仓库。"""
    store: JsonFileStore
    collection: str = "trip_itineraries"

    def get_by_trip(self, trip_id: str) -> list[dict[str, Any]]:
        rows = self.store.read_collection(self.collection)
        return sorted(
            [r for r in rows if str(r.get("trip_id")) == trip_id],
            key=lambda r: int(r.get("day_number", 1)),
        )

    def upsert(self, trip_id: str, day_number: int, item: dict[str, Any]) -> dict[str, Any]:
        rows = self.store.read_collection(self.collection)
        existing = next(
            (r for r in rows if str(r.get("trip_id")) == trip_id and int(r.get("day_number", 1)) == day_number),
            None,
        )
        item["trip_id"] = trip_id
        item["day_number"] = day_number
        if existing:
            existing.update(item)
        else:
            item["id"] = f"itin-{trip_id}-d{day_number}"
            rows.append(item)
        self.store.write_collection(self.collection, rows)
        return existing or item

    def replace_all(self, trip_id: str, days: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = self.store.read_collection(self.collection)
        rows = [r for r in rows if str(r.get("trip_id")) != trip_id]
        results = []
        for i, d in enumerate(days, 1):
            item = {
                "id": f"itin-{trip_id}-d{i}",
                "trip_id": trip_id,
                "day_number": i,
                "title": d.get("title", ""),
                "location": d.get("location", ""),
                "description": d.get("description", ""),
            }
            rows.append(item)
            results.append(item)
        self.store.write_collection(self.collection, rows)
        return results


@dataclass(slots=True)
class WorkflowExecutionRepository:
    """工作流执行记录仓库（替代 trip.workflow_status JSON）。"""
    store: JsonFileStore
    collection: str = "workflow_executions"

    def get_by_trip(self, trip_id: str) -> list[dict[str, Any]]:
        return [r for r in self.store.read_collection(self.collection) if str(r.get("trip_id")) == trip_id]

    def mark(self, trip_id: str, step_key: str, operator_id: str = "", detail: dict | None = None) -> dict[str, Any]:
        rows = self.store.read_collection(self.collection)
        existing = next(
            (r for r in rows if str(r.get("trip_id")) == trip_id and r.get("step_key") == step_key),
            None,
        )
        now = datetime.now(tz=UTC).isoformat()
        item = {
            "trip_id": trip_id,
            "step_key": step_key,
            "completed": True,
            "completed_at": now,
            "operator_id": operator_id,
            "detail": detail or {},
        }
        if existing:
            existing.update(item)
        else:
            item["id"] = f"wf-{trip_id}-{step_key}"
            rows.append(item)
        self.store.write_collection(self.collection, rows)
        return existing or item

    def get_status_map(self, trip_id: str) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for r in self.get_by_trip(trip_id):
            result[r["step_key"]] = r
        return result


@dataclass(slots=True)
class LifecyclePlaybookRepository:
    """流程剧本仓库。"""
    store: JsonFileStore
    collection: str = "lifecycle_playbook"

    def list_all(self) -> list[dict[str, Any]]:
        rows = self.store.read_collection(self.collection)
        return sorted(rows, key=lambda r: int(r.get("sort_order", 100)))

    def list_by_stage(self, stage: str) -> list[dict[str, Any]]:
        return [r for r in self.list_all() if r.get("stage") == stage]


@dataclass(slots=True)
class ProjectNotificationConfigRepository:
    store: JsonFileStore
    collection: str = "project_notification_configs"

    def list(self, *, tenant_id: str | None = None) -> list[dict[str, Any]]:
        items = self.store.read_collection(self.collection)
        if not tenant_id:
            return items
        return [item for item in items if item.get("tenant_id") == tenant_id]

    def get(self, project_id: str, *, tenant_id: str) -> dict[str, Any] | None:
        for item in self.list(tenant_id=tenant_id):
            if str(item.get("project_id") or "") == project_id:
                return item
        return None

    def upsert(self, payload: dict[str, Any]) -> dict[str, Any]:
        item = dict(payload)
        item["tenant_id"] = _normalize_tenant_id(item.get("tenant_id"))
        item["project_id"] = str(item.get("project_id") or "").strip()
        if not item["project_id"]:
            raise ValueError("project_id is required")
        item["project_name"] = str(item.get("project_name") or "")
        item["weather_enabled"] = bool(item.get("weather_enabled", True))
        item["qweather_credential_id"] = str(item.get("qweather_credential_id") or "")
        item["qweather_location_id"] = str(item.get("qweather_location_id") or "")
        item["qweather_lat"] = str(item.get("qweather_lat") or "")
        item["qweather_lon"] = str(item.get("qweather_lon") or "")
        item["weather_alert_thresholds"] = _parse_json_object(item.get("weather_alert_thresholds"))
        item["sms_provider"] = str(item.get("sms_provider") or "aliyun")
        item["sms_sign_name"] = str(item.get("sms_sign_name") or "")
        item["sms_template_code_normal"] = str(item.get("sms_template_code_normal") or "")
        item["sms_template_code_weather_alert"] = str(
            item.get("sms_template_code_weather_alert") or ""
        )
        item["manual_takeover_target"] = str(item.get("manual_takeover_target") or "")
        if not item.get("created_at"):
            item["created_at"] = datetime.now(tz=UTC).isoformat()
        item["updated_at"] = datetime.now(tz=UTC).isoformat()
        return self.store.upsert(self.collection, item, key="project_id")
