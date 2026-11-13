from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.modules.integration.persistence import JsonFileStore


@dataclass(slots=True)
class TripAssignmentRepository:
    """Tenant-scoped guide/member assignment for trips.

    Assignments live in a separate collection so both JSON and MySQL backends
    work without changing the trip table.
    """

    store: JsonFileStore
    collection: str = "trip_assignments"

    def _rows(self) -> list[dict]:
        return list(self.store.read_collection(self.collection))

    def list_user_ids(self, trip_id: str, tenant_id: str) -> list[str]:
        return sorted(
            {
                str(row.get("user_id") or "")
                for row in self._rows()
                if str(row.get("trip_id") or "") == trip_id
                and str(row.get("tenant_id") or "") == tenant_id
                and row.get("user_id")
            }
        )

    def list_trip_ids(self, user_id: str, tenant_id: str) -> set[str]:
        return {
            str(row.get("trip_id") or "")
            for row in self._rows()
            if str(row.get("user_id") or "") == user_id
            and str(row.get("tenant_id") or "") == tenant_id
            and row.get("trip_id")
        }

    def set_assignments(
        self,
        trip_id: str,
        tenant_id: str,
        user_ids: list[str],
    ) -> list[str]:
        rows = [
            row
            for row in self._rows()
            if not (
                str(row.get("trip_id") or "") == trip_id
                and str(row.get("tenant_id") or "") == tenant_id
            )
        ]
        now = datetime.now(tz=UTC).isoformat()
        assigned = sorted({str(user_id) for user_id in user_ids if user_id})
        for user_id in assigned:
            rows.append(
                {
                    "id": f"{tenant_id}:{trip_id}:{user_id}",
                    "tenant_id": tenant_id,
                    "trip_id": trip_id,
                    "user_id": user_id,
                    "created_at": now,
                }
            )
        self.store.write_collection(self.collection, rows)
        return assigned

    def delete_for_trip(self, trip_id: str, tenant_id: str) -> None:
        rows = [
            row
            for row in self._rows()
            if not (
                str(row.get("trip_id") or "") == trip_id
                and str(row.get("tenant_id") or "") == tenant_id
            )
        ]
        self.store.write_collection(self.collection, rows)
