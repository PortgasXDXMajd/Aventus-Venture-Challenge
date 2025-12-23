from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, StrictBool, field_validator

class BusTelemetryIn(BaseModel):
    bus_id: str = Field(..., min_length=1, max_length=64)
    latitude: float = Field(..., description="Decimal degrees", ge=-90, le=90)
    longitude: float = Field(..., description="Decimal degrees", ge=-180, le=180)
    temperature_c: float = Field(..., description="Cabin temperature in Celsius", ge=-50, le=100)
    smoke_detected: StrictBool = Field(..., description="Smoke sensor boolean (true/false only)")
    timestamp: Optional[datetime] = Field(
        default=None, description="Optional device timestamp; if missing, server time is used"
    )

    @field_validator("bus_id", mode="before")
    @classmethod
    def strip_bus_id(cls, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("bus_id must be a string")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("bus_id must not be empty")
        return cleaned


class BusTelemetry(BaseModel):
    bus_id: str
    latitude: float
    longitude: float
    temperature_c: float
    smoke_detected: bool
    timestamp: datetime


class TelemetryAggregates(BaseModel):
    bus_id: str
    window: str = Field(..., description="Window used for aggregation, e.g. 1h or 24h")
    count: int = Field(..., description="Number of telemetry points in the window")
    temperature_min: Optional[float] = Field(None, description="Minimum temperature over window")
    temperature_avg: Optional[float] = Field(None, description="Average temperature over window")
    temperature_max: Optional[float] = Field(None, description="Maximum temperature over window")
