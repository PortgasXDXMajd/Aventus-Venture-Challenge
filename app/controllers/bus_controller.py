from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query, status
from typing import AsyncIterator, Generator, List, Optional
from core.config import get_settings
from db.session import get_session_factory
from repos.bus_repository import BusRepository
from repos.influx_repository import TelemetryRepository
from schemas.response import ResponseModel
from schemas.bus import Bus
from schemas.telemetry import BusTelemetry, TelemetryAggregates
from services.bus_service import BusService
from services.telemetry_service import TelemetryService

router = APIRouter(prefix="/api/v1/buses", tags=["buses"])

async def get_db_session() -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session

def get_service(session: AsyncSession = Depends(get_db_session)) -> BusService:
    repository = BusRepository(session)
    return BusService(repository)

def get_telemetry_service() -> Generator[TelemetryService, None, None]:
    repository = TelemetryRepository()
    service = TelemetryService(repository)
    
    yield service



@router.get("/{bus_id}/telemetry/latest", response_model=ResponseModel[BusTelemetry])
async def get_latest_bus_telemetry(
    bus_id: str, telemetry_service: TelemetryService = Depends(get_telemetry_service)
) -> ResponseModel[BusTelemetry]:
    
    latest = telemetry_service.get_latest_bus_telemetry(bus_id)
    return ResponseModel(status=status.HTTP_200_OK, message="Success", data=latest)

@router.get("/{bus_id}/telemetry/history", response_model=ResponseModel[List[BusTelemetry]])
async def get_bus_telemetry_history(
    bus_id: str,
    start: Optional[datetime] = Query(None, description="Start time Defaults to end-24h."),
    end: Optional[datetime] = Query(None, description="End time. Defaults to now."),
    limit: int = Query(100, ge=1, le=5000, description="Maximum points to return"),
    telemetry_service: TelemetryService = Depends(get_telemetry_service),
) -> ResponseModel[List[BusTelemetry]]:
    
    history = telemetry_service.get_bus_telemetry_history(bus_id, start, end, limit)
    return ResponseModel(status=status.HTTP_200_OK, message="Success", data=history)


@router.get("/{bus_id}/telemetry/aggregates", response_model=ResponseModel[TelemetryAggregates])
async def get_bus_telemetry_aggregates(
    bus_id: str,
    window: str = Query("1h", min_length=1, description="Window duration, e.g. 15m, 1h, 24h"),
    telemetry_service: TelemetryService = Depends(get_telemetry_service),
) -> ResponseModel[TelemetryAggregates]:
    
    aggregates = telemetry_service.get_bus_telemetry_aggregates(bus_id, window)
    return ResponseModel(status=status.HTTP_200_OK, message="Success", data=aggregates)
