from typing import List, Optional
from fastapi import HTTPException, status
from datetime import datetime, timedelta, timezone
from repos.influx_repository import TelemetryRepository
from schemas.telemetry import BusTelemetryIn, BusTelemetry, TelemetryAggregates

class TelemetryService:
    def __init__(self, repository: TelemetryRepository):
        self._repository = repository

    def ingest_bus_telemetry(self, payload: BusTelemetryIn) -> BusTelemetry:
        normalized = self._normalize(payload)
        try:
            self._repository.write_bus_telemetry(normalized)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to persist telemetry",
            ) from exc
        return normalized

    def ingest_bus_telemetry_batch(self, payloads: List[BusTelemetryIn]) -> List[BusTelemetry]:
        if not payloads:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No telemetry provided")
        normalized = [self._normalize(payload) for payload in payloads]
        try:
            self._repository.write_bus_telemetry_batch(normalized)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to persist telemetry batch",
            ) from exc
        return normalized

    def get_latest_bus_telemetry(self, bus_id: str) -> BusTelemetry:
        latest = self._repository.get_latest_bus_telemetry(bus_id)
        if latest is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No telemetry found")
        return latest

    def get_bus_telemetry_history(
        self, bus_id: str, start: Optional[datetime], end: Optional[datetime], limit: int
    ) -> List[BusTelemetry]:
        if end is None:
            end = datetime.now(timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        if start is None:
            start = end - timedelta(hours=24)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)

        if start >= end:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start must be before end")

        # Protect Influx from excessive responses
        limit = min(max(limit, 1), 5000)

        return self._repository.get_bus_telemetry_history(bus_id, start, end, limit)

    def get_bus_telemetry_aggregates(self, bus_id: str, window: str) -> TelemetryAggregates:
        window = window.strip()
        if not window:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="window is required")

        metrics = self._repository.get_bus_telemetry_aggregates(bus_id, window)
        if metrics is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No telemetry found")

        return TelemetryAggregates(
            bus_id=bus_id,
            window=window,
            count=int(metrics.get("count", 0)),
            temperature_min=metrics.get("temperature_min"),
            temperature_avg=metrics.get("temperature_avg"),
            temperature_max=metrics.get("temperature_max"),
        )

    def _normalize(self, payload: BusTelemetryIn) -> BusTelemetry:
        lat = round(payload.latitude, 6)
        lon = round(payload.longitude, 6)
        temp = round(payload.temperature_c, 2)
        timestamp = payload.timestamp or datetime.now(timezone.utc)

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        return BusTelemetry(
            bus_id=payload.bus_id,
            latitude=lat,
            longitude=lon,
            temperature_c=temp,
            smoke_detected=bool(payload.smoke_detected),
            timestamp=timestamp,
        )
