from datetime import datetime
from typing import Dict, List, Optional

from influxdb_client.client.write.point import Point

from core.config import get_settings
from db.session import get_influx_query_api, get_influx_query_api, get_influx_write_api
from schemas.telemetry import BusTelemetry

from influxdb_client.client.write_api import WriteOptions

class TelemetryRepository:
    def __init__(self):
        self.settings = get_settings()
        self._bucket = self.settings.influx_bucket
        self._write_api = get_influx_write_api()
        self._query_api = get_influx_query_api()

    def write_bus_telemetry(self, telemetry: BusTelemetry) -> None:
        self.write_bus_telemetry_batch([telemetry])

    def write_bus_telemetry_batch(self, telemetries: List[BusTelemetry]) -> None:
        if not telemetries:
            return

        points: List[Point] = []

        for t in telemetries:
            points.append(
                Point("bus_telemetry")
                .tag("bus_id", t.bus_id)
                .field("latitude", t.latitude)
                .field("longitude", t.longitude)
                .field("temperature_c", t.temperature_c)
                .field("smoke_detected", int(t.smoke_detected))
                .time(t.timestamp or datetime.utcnow())
            )

        self._write_api.write(
            bucket=self.settings.influx_bucket,
            record=points,
        )

    def get_latest_bus_telemetry(self, bus_id: str) -> Optional[BusTelemetry]:
        flux = f"""
        from(bucket: "{self.settings.influx_bucket}")
          |> range(start: -7d)
          |> filter(fn: (r) => r["_measurement"] == "bus_telemetry")
          |> filter(fn: (r) => r["bus_id"] == "{bus_id}")
          |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: 1)
        """

        tables = self._query_api.query(flux)
        if not tables:
            return None

        for table in tables:
            if not table.records:
                continue

            rec = table.records[0]
            return BusTelemetry(
                bus_id=rec.values["bus_id"],
                latitude=float(rec.values["latitude"]),
                longitude=float(rec.values["longitude"]),
                temperature_c=float(rec.values["temperature_c"]),
                smoke_detected=bool(rec.values.get("smoke_detected", 0)),
                timestamp=rec.get_time(),
            )

        return None

    def get_bus_telemetry_history(
        self,
        bus_id: str,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> List[BusTelemetry]:
        flux = f"""
        from(bucket: "{self.settings.influx_bucket}")
          |> range(start: {start.isoformat()}, stop: {end.isoformat()})
          |> filter(fn: (r) => r["_measurement"] == "bus_telemetry")
          |> filter(fn: (r) => r["bus_id"] == "{bus_id}")
          |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: {limit})
        """

        tables = self._query_api.query(flux)
        results: List[BusTelemetry] = []

        for table in tables:
            for rec in table.records:
                results.append(
                    BusTelemetry(
                        bus_id=rec.values["bus_id"],
                        latitude=float(rec.values["latitude"]),
                        longitude=float(rec.values["longitude"]),
                        temperature_c=float(rec.values["temperature_c"]),
                        smoke_detected=bool(rec.values.get("smoke_detected", 0)),
                        timestamp=rec.get_time(),
                    )
                )

        return results

    def get_bus_telemetry_aggregates(
        self, bus_id: str, window: str
    ) -> Optional[Dict[str, float]]:
        flux = f"""
        base = from(bucket: "{self.settings.influx_bucket}")
          |> range(start: -{window})
          |> filter(fn: (r) => r["_measurement"] == "bus_telemetry")
          |> filter(fn: (r) => r["bus_id"] == "{bus_id}")

        mean = base
          |> filter(fn: (r) => r["_field"] == "temperature_c")
          |> mean()
          |> set(key: "metric", value: "temperature_avg")

        min = base
          |> filter(fn: (r) => r["_field"] == "temperature_c")
          |> min()
          |> set(key: "metric", value: "temperature_min")

        max = base
          |> filter(fn: (r) => r["_field"] == "temperature_c")
          |> max()
          |> set(key: "metric", value: "temperature_max")

        count = base
          |> filter(fn: (r) => r["_field"] == "temperature_c")
          |> count()
          |> toFloat()
          |> set(key: "metric", value: "count")

        union(tables: [mean, min, max, count])
          |> keep(columns: ["metric", "_value"])
        """

        tables = self._query_api.query(flux)
        if not tables:
            return None

        metrics: Dict[str, float] = {}
        for table in tables:
            for rec in table.records:
                metrics[str(rec.values["metric"])] = float(rec.get_value())

        return metrics or None