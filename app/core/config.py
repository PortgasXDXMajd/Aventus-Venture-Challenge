from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AV Challenge"
    influx_url: str = "http://influxdb:8086"
    influx_org: str = "demo"
    influx_bucket: str = "telemetry"
    influx_token: str = "local-dev-token"
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/postgres"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
