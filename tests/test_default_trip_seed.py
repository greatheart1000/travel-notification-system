from __future__ import annotations

from app.api.http import _seed_default_trips
from app.modules.integration.persistence import JsonFileStore, TripRepository


def test_seed_default_trips_keeps_existing_and_backfills_defaults(tmp_path) -> None:
    store = JsonFileStore(base_dir=tmp_path)
    repository = TripRepository(store=store)
    repository.create(
        {
            "id": "trip-user-created",
            "destination": "用户自建线路",
            "tenant_id": "tenant-a",
        }
    )

    _seed_default_trips(repository)

    trip_ids = {str(item.get("id") or "") for item in repository.list()}
    assert "trip-user-created" in trip_ids
    assert "trip-default-pretrip" in trip_ids
    assert "trip-default-ontrip" in trip_ids
    assert "trip-default-posttrip" in trip_ids
