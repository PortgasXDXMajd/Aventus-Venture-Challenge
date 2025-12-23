from typing import List, Optional
from uuid import UUID, uuid4

from schemas.bus import Bus
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession



BUS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS buses (
    bus_id TEXT PRIMARY KEY,
    plate_number TEXT,
    driver_name TEXT,
    route_name TEXT,
    api_key TEXT NOT NULL
);
"""

DEFAULT_BUS_KEYS: dict[str, UUID] = {
    "bus-1": UUID("7b0c3c0f-2f0a-4f93-9f3e-5c7e0c123001"),
    "bus-2": UUID("8e9a7b2d-1a23-4c45-8f17-03fa5a5f5b02"),
    "bus-3": UUID("0a815d8a-7cb2-4fba-8e44-9c3d5adcf603"),
}

class BusRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def init_table(self) -> None:
        await self._session.execute(text(BUS_TABLE_SQL))
        await self._session.execute(text("ALTER TABLE buses ADD COLUMN IF NOT EXISTS api_key TEXT"))
        # Ensure any pre-existing rows have an API key
        result = await self._session.execute(text("SELECT bus_id, api_key FROM buses"))
        for row in result.mappings().all():
            if row.get("api_key"):
                continue
            default_key = DEFAULT_BUS_KEYS.get(row["bus_id"], uuid4())
            await self._session.execute(
                text("UPDATE buses SET api_key = :api_key WHERE bus_id = :bus_id"),
                {"api_key": str(default_key), "bus_id": row["bus_id"]},
            )
        await self._session.execute(text("ALTER TABLE buses ALTER COLUMN api_key SET NOT NULL"))
        await self._session.commit()

    async def seed_default_async(self) -> None:
        defaults = [
            Bus(
                bus_id="bus-1",
                plate_number="ABC-001",
                driver_name="Majd",
                route_name="North Route",
                api_key=DEFAULT_BUS_KEYS["bus-1"],
            ),
            Bus(
                bus_id="bus-2",
                plate_number="ABC-002",
                driver_name="Raymo",
                route_name="South Route",
                api_key=DEFAULT_BUS_KEYS["bus-2"],
            ),
            Bus(
                bus_id="bus-3",
                plate_number="ABC-003",
                driver_name="Robert",
                route_name="East Route",
                api_key=DEFAULT_BUS_KEYS["bus-3"],
            ),
        ]
        for bus in defaults:
            await self.insert_if_missing(bus)

    async def get_all_async(self) -> List[Bus]:
        result = await self._session.execute(
            text("SELECT bus_id, plate_number, driver_name, route_name, api_key FROM buses")
        )
        rows = result.mappings().all()
        return [Bus(**row) for row in rows]

    async def get_by_id_async(self, bus_id: str) -> Optional[Bus]:
        result = await self._session.execute(
            text("SELECT bus_id, plate_number, driver_name, route_name, api_key FROM buses WHERE bus_id = :bus_id"),
            {"bus_id": bus_id},
        )
        row = result.mappings().first()
        return Bus(**row) if row else None

    async def upsert_async(self, bus: Bus) -> Bus:
        payload = bus.model_dump()
        payload["api_key"] = str(payload["api_key"])
        await self._session.execute(
            text(
                """
                INSERT INTO buses (bus_id, plate_number, driver_name, route_name, api_key)
                VALUES (:bus_id, :plate_number, :driver_name, :route_name, :api_key)
                ON CONFLICT (bus_id) DO UPDATE SET
                    plate_number = EXCLUDED.plate_number,
                    driver_name = EXCLUDED.driver_name,
                    route_name = EXCLUDED.route_name,
                    api_key = EXCLUDED.api_key
                """
            ),
            payload,
        )
        await self._session.commit()
        return bus

    async def insert_if_missing(self, bus: Bus) -> Bus:
        payload = bus.model_dump()
        payload["api_key"] = str(payload["api_key"])
        await self._session.execute(
            text(
                """
                INSERT INTO buses (bus_id, plate_number, driver_name, route_name, api_key)
                VALUES (:bus_id, :plate_number, :driver_name, :route_name, :api_key)
                ON CONFLICT (bus_id) DO NOTHING
                """
            ),
            payload,
        )
        await self._session.commit()
        return bus
