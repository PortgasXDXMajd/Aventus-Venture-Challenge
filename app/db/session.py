from functools import lru_cache
from influxdb_client.client.influxdb_client import InfluxDBClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from influxdb_client.client.write_api import WriteOptions

from core.config import get_settings

@lru_cache()
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)


@lru_cache()
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = get_engine()
    return async_sessionmaker(bind=engine, expire_on_commit=False)


@lru_cache()
def get_influx_client() -> InfluxDBClient:
    settings = get_settings()

    return InfluxDBClient(
        url=str(settings.influx_url),
        token=settings.influx_token,
        org=settings.influx_org,
    )


@lru_cache()
def get_influx_write_api():
    client = get_influx_client()

    return client.write_api(
        write_options=WriteOptions(
            batch_size=500,
            flush_interval=1000,
            retry_interval=5000,
            max_retries=3,
        )
    )


@lru_cache()
def get_influx_query_api():
    client = get_influx_client()
    return client.query_api()
