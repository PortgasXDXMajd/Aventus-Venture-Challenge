from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

class Bus(BaseModel):
    bus_id: str = Field(..., min_length=1, max_length=64)
    plate_number: Optional[str] = Field(None, max_length=32)
    driver_name: Optional[str] = Field(None, max_length=128)
    route_name: Optional[str] = Field(None, max_length=128)
    api_key: UUID = Field(...)

    @field_validator("bus_id", mode="before")
    @classmethod
    def strip_bus_id(cls, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("bus_id must be a string")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("bus_id must not be empty")
        return cleaned
