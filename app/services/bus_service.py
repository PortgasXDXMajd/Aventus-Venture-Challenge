from typing import List
from schemas.bus import Bus
from repos.bus_repository import BusRepository

class BusService:
    def __init__(self, repository: BusRepository):
        self._repository = repository

    async def list_buses(self) -> List[Bus]:
        return await self._repository.get_all_async()

    async def get_bus(self, bus_id: str) -> Bus | None:
        return await self._repository.get_by_id_async(bus_id)

    async def upsert_bus(self, bus: Bus) -> Bus:
        return await self._repository.upsert_async(bus)
