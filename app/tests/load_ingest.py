import asyncio
from datetime import datetime, timedelta, timezone
import os
import random
import time

import httpx

TOTAL_REQUESTS = int(os.getenv("INGEST_TOTAL", "10000"))
CONCURRENCY = int(os.getenv("INGEST_CONCURRENCY", "100"))
BASE_URL = os.getenv("INGEST_BASE_URL", "http://localhost:8000")

BUSES = [
    {
        "bus_id": "bus-1",
        "api_key": os.getenv("INGEST_API_KEY_BUS1", "7b0c3c0f-2f0a-4f93-9f3e-5c7e0c123001"),
    },
    {
        "bus_id": "bus-2",
        "api_key": os.getenv("INGEST_API_KEY_BUS2", "8e9a7b2d-1a23-4c45-8f17-03fa5a5f5b02"),
    },
    {
        "bus_id": "bus-3",
        "api_key": os.getenv("INGEST_API_KEY_BUS3", "0a815d8a-7cb2-4fba-8e44-9c3d5adcf603"),
    },
]


async def send_request(client: httpx.AsyncClient, idx: int, base_time: datetime) -> None:
    bus = BUSES[idx % len(BUSES)]
    bus_id = bus["bus_id"]
    timestamp = base_time - timedelta(seconds=30 * idx)
    payload = {
        "bus_id": bus_id,
        "latitude": 25.0 + random.random(),
        "longitude": 55.0 + random.random(),
        "temperature_c": 20 + random.random() * 10,
        "smoke_detected": random.choice([True, False]),
        "timestamp": timestamp.isoformat(),
    }
    headers = {"X-Bus-Api-Key": bus["api_key"]}
    response = await client.post(f"{BASE_URL}/api/v1/ingest/bus", json=payload, headers=headers, timeout=10)
    response.raise_for_status()


async def run_load_test() -> None:
    limiter = asyncio.Semaphore(CONCURRENCY)
    start = time.perf_counter()
    base_time = datetime.now(timezone.utc)

    async with httpx.AsyncClient() as client:
        tasks = []
        for i in range(TOTAL_REQUESTS):
            await limiter.acquire()

            async def wrapped(idx: int) -> None:
                try:
                    await send_request(client, idx, base_time)
                finally:
                    limiter.release()

            tasks.append(asyncio.create_task(wrapped(i)))

        await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start
    rps = TOTAL_REQUESTS / elapsed if elapsed else 0
    print(f"Sent {TOTAL_REQUESTS} requests in {elapsed:.2f}s ({rps:.2f} req/s) with concurrency={CONCURRENCY}")


if __name__ == "__main__":
    asyncio.run(run_load_test())
