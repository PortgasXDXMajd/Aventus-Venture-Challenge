from typing import AsyncIterator, Generator, List

from fastapi import APIRouter, Depends, Header, HTTPException, status

from db.session import get_session_factory
from repos.bus_repository import BusRepository
from repos.influx_repository import TelemetryRepository
from schemas.response import ResponseModel
from schemas.telemetry import BusTelemetryIn, BusTelemetry
from services.bus_service import BusService
from services.telemetry_service import TelemetryService

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])

def get_service() -> Generator[TelemetryService, None, None]:
    repository = TelemetryRepository()
    service = TelemetryService(repository)
    yield service


async def get_bus_service() -> AsyncIterator[BusService]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        repository = BusRepository(session)
        yield BusService(repository)


async def _validate_bus_api_key(bus_ids: List[str], api_key: str | None, bus_service: BusService) -> None:
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    unique_ids = {bus_id.strip() for bus_id in bus_ids if bus_id}
    if not unique_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No bus telemetry provided")
    if len(unique_ids) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch telemetry must belong to a single bus",
        )
    bus_id = unique_ids.pop()
    bus = await bus_service.get_bus(bus_id)
    if bus is None or str(bus.api_key) != api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")


async def require_single_bus_api_key(
    payload: BusTelemetryIn,
    api_key: str | None = Header(None, alias="X-Bus-Api-Key"),
    bus_service: BusService = Depends(get_bus_service),
) -> None:
    await _validate_bus_api_key([payload.bus_id], api_key, bus_service)


async def require_batch_bus_api_key(
    payloads: List[BusTelemetryIn],
    api_key: str | None = Header(None, alias="X-Bus-Api-Key"),
    bus_service: BusService = Depends(get_bus_service),
) -> None:
    await _validate_bus_api_key([payload.bus_id for payload in payloads], api_key, bus_service)




@router.post("/bus", response_model=ResponseModel[BusTelemetry], status_code=status.HTTP_202_ACCEPTED)
async def ingest_bus(
    payload: BusTelemetryIn,
    service: TelemetryService = Depends(get_service),
    _: None = Depends(require_single_bus_api_key),
) -> ResponseModel[BusTelemetry]:
    normalized = service.ingest_bus_telemetry(payload)
    return ResponseModel(status=status.HTTP_202_ACCEPTED, message="Success", data=normalized)


@router.post(
    "/bus/batch",
    response_model=ResponseModel[List[BusTelemetry]],
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_bus_batch(
    payloads: List[BusTelemetryIn],
    service: TelemetryService = Depends(get_service),
    _: None = Depends(require_batch_bus_api_key),
) -> ResponseModel[List[BusTelemetry]]:
    normalized = service.ingest_bus_telemetry_batch(payloads)
    return ResponseModel(status=status.HTTP_202_ACCEPTED, message="Success", data=normalized)
