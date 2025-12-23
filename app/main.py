import asyncio
import logging

from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager

from controllers import bus_controller, telemetry_controller
from core.config import get_settings
from db.session import get_influx_client, get_influx_write_api, get_session_factory
from repos.bus_repository import BusRepository
from schemas.response import ResponseModel

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger(__name__)
    session_factory = get_session_factory()
    attempts = 0
    while attempts < 5:
        try:
            async with session_factory() as session:
                repo = BusRepository(session)
                await repo.init_table()
                await repo.seed_default_async()
            break
        except Exception as exc:
            attempts += 1
            wait = 2 * attempts
            logger.warning("DB init attempt %s failed (%s); retrying in %ss", attempts, exc, wait)
            await asyncio.sleep(wait)
    else:
        logger.error("DB init failed after retries; app may not serve bus endpoints")

    get_influx_client()
    get_influx_write_api()

    yield

    write_api = get_influx_write_api()
    client = get_influx_client()
    write_api.flush()
    client.close()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(telemetry_controller.router)
app.include_router(bus_controller.router)


@app.get("/", response_model=ResponseModel[None])
def read_root() -> ResponseModel[None]:
    return ResponseModel(status=200, message="Hello AV Challenge", data=None)
