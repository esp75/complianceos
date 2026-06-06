# Orekit service — wire contract (v0)

The FastAPI BFF ↔ Orekit interface. REST/JSON over HTTP, per [ADR-0013](../../../adr/0013-orekit-service-contract-rest-over-grpc.md).
This is the single source of truth for request/response shapes; the Python `OrekitClient`
(`app/app/clients/orekit.py`) and the Java controllers must both conform to it.

## Conventions

- **Transport**: HTTP/1.1, JSON request and response bodies, `Content-Type: application/json`.
- **Base URL** (in-cluster): `http://orekit:8090`. Dev host: `http://localhost:8090`.
- **Distances**: kilometres (km). **Velocities**: km/s.
- **Times**: UTC, ISO-8601 (`2026-06-06T00:00:00Z`).
- **Frames**: one of `EME2000`, `ITRF`, `TEME`.
- **Vectors**: `[x, y, z]` arrays of three doubles.
- **Network**: called only from inside the `celestia-l1` network (ADR-0002). No public exposure.

## Error envelope

Every non-2xx response carries:

```json
{ "error": { "code": "string", "message": "human-readable detail" } }
```

- `400 Bad Request` — malformed TLE (checksum/column/epoch), bad frame name, invalid window.
  `code` ∈ `{ "invalid_tle", "invalid_frame", "invalid_window", "invalid_request" }`.
- `503 Service Unavailable` — orekit-data not yet loaded. `code` = `"not_ready"`.
- `500 Internal Server Error` — unexpected Orekit/propagation failure. `code` = `"internal"`.

## Endpoints

### `GET /healthz` — liveness
Never touches Orekit. `200 {"status":"ok"}` whenever the process is up.

### `GET /readyz` — readiness
`200 {"status":"ready"}` only once `OrekitDataConfig` confirms orekit-data is loaded;
otherwise `503` with `{"error":{"code":"not_ready","message":"..."}}`.

### `POST /propagate`
Propagate a TLE to a target epoch.

Request:
```json
{
  "tle": { "line1": "1 25544U ...", "line2": "2 25544 ..." },
  "epoch": "2026-06-06T00:00:00Z"
}
```
Response `200`:
```json
{
  "position": [x, y, z],
  "velocity": [vx, vy, vz],
  "frame": "TEME",
  "epoch": "2026-06-06T00:00:00Z"
}
```
Notes: TLE propagation is naturally in `TEME`. `frame` echoes the frame the state is
expressed in.

### `POST /conjunction`
Sampled minimum-miss-distance screening between two objects over a window. **v0 does NOT
compute probability-of-collision** (no covariance input) — it reports geometric range minima
only (ADR-0013 decision 4).

Request:
```json
{
  "tle1": { "line1": "...", "line2": "..." },
  "tle2": { "line1": "...", "line2": "..." },
  "window": { "start": "2026-06-06T00:00:00Z", "end": "2026-06-06T06:00:00Z", "stepSeconds": 60 }
}
```
Response `200`:
```json
{
  "events": [
    { "epoch": "2026-06-06T01:23:00Z", "missDistanceKm": 4.21, "relativeSpeedKmS": 11.3 }
  ],
  "minMissDistanceKm": 4.21
}
```
`events` are the local range minima found in the window (closest-approach samples). An empty
`events` list with a populated `minMissDistanceKm` means no local minimum dipped below the
reporting threshold but the global minimum is still reported.

### `POST /frame_convert`
Convert a state vector between reference frames.

Request:
```json
{
  "state": { "position": [x,y,z], "velocity": [vx,vy,vz], "epoch": "2026-06-06T00:00:00Z" },
  "fromFrame": "TEME",
  "toFrame": "EME2000"
}
```
Response `200`:
```json
{
  "position": [x, y, z],
  "velocity": [vx, vy, vz],
  "frame": "EME2000",
  "epoch": "2026-06-06T00:00:00Z"
}
```

## orekit-data provisioning

The service requires the Orekit data set (EOP, leap seconds, gravity models). Provisioned by
`scripts/fetch-orekit-data.sh` into a gitignored directory, mounted read-only at `/orekit-data`
(ADR-0013 decision 5). `OrekitDataConfig` registers a `DirectoryCrawler` over that path at
startup; `/readyz` gates on it. The data set is NOT baked into the image.

## Version pin

Running jar: `org.orekit:orekit:13.1.5` (released). Audited vendored source line:
`external/orekit/` @ `fb3a845...` (`14.0-SNAPSHOT`, develop). The skew is intentional and
tracked in `docs/upstream-watch.md` (ADR-0013 decision 6).
