# Students + Buses Tracking System

It :

- Tracks **bus location + environment** (temperature, smoke, etc.)
- Tracks **student vitals** (heart rate, etc.) via wristbands
- Generates **alerts**
- Serves **two apps**:
  - **Admin web** (ministry/schools): fleet + incidents across country
  - **Parent mobile**: child vitals + bus live location + notifications

---

::: mermaid
flowchart LR
  WB[Wristband]
  BUS[Bus Unit]
  INGRESS[IoT Ingress - Azure IoT Hub]
  KAFKA[Kafka]
  PROC[Stream Processor]
  DB[(Databases)]
  ALERT[Alert Engine - Notifications]
  API[Backend API]
  ADMIN[Admin Web App]
  PARENT[Parent Mobile App]

  WB --> INGRESS --> KAFKA --> PROC --> DB
  BUS --> INGRESS
  PROC --> ALERT

  API --> DB
  ADMIN --> API
  PARENT --> API
  ALERT --> DB

:::

---

## Devices

- **Wristband**: sends vitals (heart rate, ...) every N seconds over cellular.
- **Bus Unit**: sends GPS (lat/lon) + environment (CO2, temperature, smoke) every N seconds over cellular.

---

## Data Flow

1. Devices send telemetry to **IoT Ingress (Azure IoT Hub)** (MQTT + device auth).
2. Ingress routes messages to **Kafka** topics (e.g. bus info, wristband vitals).
3. **Stream Processor** consumes Kafka:
   - validates + remove duplicates events
   - updates “latest state” in Main DB
   - stores history (time-series DB)
   - triggers alerts (smoke/CO2 high, abnormal vitals, device offline, route deviation)
4. **Backend API** serves Admin + Parent apps and reads from storage.

---

## Databases

- **Main DB (Operational / Postgres)**: buses, children, parents, assignments, alerts/incidents + latest-state
- **Time-series DB**: bus telemetry history + wristband vitals history

---

## Core API Tracking Endpoints

Base path: `/api/v1`

---

## 1. Get bus latest telemetry

**GET** `/buses/{bus_id}/telemetry/latest`

**Purpose**  
Return the most recent telemetry snapshot for a bus (location + environment).

###@ Used by

- Admin web
- Parent app

**Data source**  

- Main DB

---

## 2. Get bus telemetry history

**GET** `/buses/{bus_id}/telemetry/history`

**Purpose**  
Return raw telemetry points for a bus over a time range.

**Used by**  

- Route replay  
- Incident investigation  

**Notes**  

- Time-range query
- Limited number of points

**Data source**  

- Time-series DB

---

## 3. Get bus telemetry aggregates

**GET** `/buses/{bus_id}/telemetry/aggregates`

**Purpose**  
Return aggregated telemetry metrics over a time window (averages, min/max).

### Used by

- Dashboards (Admin or school admins)

**Data source**  

- Time-series DB

---

## 4. Ingest single bus telemetry

**POST** `/ingest/bus`

**Purpose**  
Receive telemetry from a single bus device.

**Behavior**  

- Authenticated via `X-Bus-Api-Key`

### Data flow

- Validate device  
- Store telemetry  
- Trigger downstream processing

---

## 5. Ingest batch bus telemetry

**POST** `/ingest/bus/batch`

**Purpose**  
Receive multiple telemetry points for the same bus in one request.

---

## Alerts (Generated from the Stream Processor)

- Alerts are produced by **Stream Processor** rules (vitals abnormal, smoke/CO2, offline, route deviation, etc.)
- They are sent via **Alert Engine** and stored in **Main DB**
- Apps consume them via the Backend API for history
- we push notification (e.g. Firebase)
