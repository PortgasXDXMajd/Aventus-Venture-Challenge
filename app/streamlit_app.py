import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx
import streamlit as st


DEFAULT_BASE_URL = os.getenv("STREAMLIT_BASE_URL", "http://localhost:8000")
DEFAULT_KEYS = {
    "bus-1": "7b0c3c0f-2f0a-4f93-9f3e-5c7e0c123001",
    "bus-2": "8e9a7b2d-1a23-4c45-8f17-03fa5a5f5b02",
    "bus-3": "0a815d8a-7cb2-4fba-8e44-9c3d5adcf603",
}


def _isoformat(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def call_api(
    method: str,
    base_url: str,
    path: str,
    api_key: Optional[str] = None,
    json_body: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> httpx.Response:
    headers: Dict[str, str] = {}
    if api_key:
        headers["X-Bus-Api-Key"] = api_key
    with httpx.Client(timeout=10) as client:
        resp = client.request(
            method=method,
            url=f"{base_url}{path}",
            headers=headers,
            json=json_body,
            params=params,
        )
    return resp


def render_response(resp: httpx.Response) -> None:
    try:
        payload = resp.json()
    except Exception:
        payload = {"raw": resp.text}
    if resp.is_success:
        st.success(f"{resp.status_code}")
        st.json(payload)
    else:
        st.error(f"{resp.status_code}")
        st.json(payload)


st.set_page_config(page_title="Bus Telemetry Console", page_icon="🚌", layout="wide")
st.title("Bus Telemetry Console")

with st.sidebar:
    st.header("Settings")
    base_url = st.text_input("Base URL", value=DEFAULT_BASE_URL)
    st.caption("All API calls use this base URL.")

    st.subheader("API Keys")
    bus_keys: Dict[str, str] = {}
    for bus_id, default_key in DEFAULT_KEYS.items():
        bus_keys[bus_id] = st.text_input(f"{bus_id} key", value=default_key)

    st.subheader("Load Test")
    total_requests = st.number_input("Total requests", min_value=1, max_value=20000, value=10000, step=500)
    concurrency = st.number_input("Concurrency", min_value=1, max_value=1000, value=100, step=10)
    if st.button("Run load test", type="primary"):
        env = os.environ.copy()
        env.update(
            {
                "INGEST_TOTAL": str(total_requests),
                "INGEST_CONCURRENCY": str(concurrency),
                "INGEST_BASE_URL": base_url,
                "INGEST_API_KEY_BUS1": bus_keys.get("bus-1", ""),
                "INGEST_API_KEY_BUS2": bus_keys.get("bus-2", ""),
                "INGEST_API_KEY_BUS3": bus_keys.get("bus-3", ""),
            }
        )
        with st.spinner("Running load test..."):
            result = subprocess.run(
                [sys.executable, "-u", "tests/load_ingest.py"],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                capture_output=True,
                text=True,
                env=env,
            )
        if result.returncode == 0:
            st.success(result.stdout or "Load test completed")
        else:
            st.error("Load test failed")
            st.code(result.stdout + "\n" + result.stderr)


st.markdown("### Manual Ingest")
col_ingest_left, col_ingest_right = st.columns(2)
with col_ingest_left:
    ingest_bus_id = st.selectbox("Bus ID", options=list(bus_keys.keys()), index=0)
    ingest_lat = st.number_input("Latitude", value=25.0, format="%.6f")
    ingest_lon = st.number_input("Longitude", value=55.0, format="%.6f")
    ingest_temp = st.number_input("Temperature C", value=25.0, format="%.2f")
    ingest_smoke = st.checkbox("Smoke detected", value=False)
with col_ingest_right:
    ingest_timestamp = st.text_input(
        "Timestamp (ISO8601, optional)",
        value=_isoformat(datetime.now(timezone.utc)),
    )

if st.button("Send telemetry"):
    payload = {
        "bus_id": ingest_bus_id,
        "latitude": ingest_lat,
        "longitude": ingest_lon,
        "temperature_c": ingest_temp,
        "smoke_detected": ingest_smoke,
    }
    if ingest_timestamp.strip():
        payload["timestamp"] = ingest_timestamp.strip()
    resp = call_api(
        "POST",
        base_url,
        "/api/v1/ingest/bus",
        api_key=bus_keys.get(ingest_bus_id),
        json_body=payload,
    )
    render_response(resp)


st.markdown("### Telemetry Queries")
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Latest")
    bus_choice_latest = st.selectbox("Bus for latest", options=list(bus_keys.keys()), key="latest_bus")
    if st.button("Get latest"):
        resp = call_api(
            "GET",
            base_url,
            f"/api/v1/buses/{bus_choice_latest}/telemetry/latest",
            api_key=bus_keys.get(bus_choice_latest),
        )
        render_response(resp)

with col2:
    st.subheader("History")
    bus_choice_history = st.selectbox("Bus for history", options=list(bus_keys.keys()), key="history_bus")
    now = datetime.now(timezone.utc)
    start_default = _isoformat(now - timedelta(days=7))
    end_default = _isoformat(now)
    start_input = st.text_input("Start (ISO8601)", value=start_default)
    end_input = st.text_input("End (ISO8601)", value=end_default)
    limit = st.number_input("Limit", min_value=1, max_value=5000, value=5000, step=100)
    if st.button("Get history"):
        params = {"start": start_input, "end": end_input, "limit": limit}
        resp = call_api(
            "GET",
            base_url,
            f"/api/v1/buses/{bus_choice_history}/telemetry/history",
            api_key=bus_keys.get(bus_choice_history),
            params=params,
        )
        render_response(resp)

with col3:
    st.subheader("Aggregates")
    bus_choice_agg = st.selectbox("Bus for aggregates", options=list(bus_keys.keys()), key="agg_bus")
    window = st.text_input("Window (e.g. 1h, 24h)", value="24h")
    if st.button("Get aggregates"):
        params = {"window": window}
        resp = call_api(
            "GET",
            base_url,
            f"/api/v1/buses/{bus_choice_agg}/telemetry/aggregates",
            api_key=bus_keys.get(bus_choice_agg),
            params=params,
        )
        render_response(resp)
