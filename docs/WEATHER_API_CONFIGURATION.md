# PikVaidya AI — Weather API Configuration & Operations Guide

**Document Version:** 1.0.0  
**Project:** PikVaidya AI  
**Module:** Weather System Configuration, Tuning & Troubleshooting  
**Author:** Senior Full-Stack Developer & Software Architect  
**Date:** November 2026  

---

## 1. Environment Variables Configuration

PikVaidya AI uses Pydantic-Settings to load configuration parameters from the environment and `.env` files. The following environment variables configure the weather subsystem:

| Variable Name | Type | Default Value | Description |
| :--- | :---: | :---: | :--- |
| `WEATHER_PROVIDER` | string | `open-meteo` | Active primary weather provider (`open-meteo`, `imd`, `fallback`) |
| `WEATHER_DEFAULT_DISTRICT` | string | `pune` | Default regional Maharashtra district when no GPS/district is given |
| `WEATHER_DEFAULT_LAT` | float | `18.5204` | Default latitude coordinate (Pune centroid) |
| `WEATHER_DEFAULT_LON` | float | `73.8567` | Default longitude coordinate (Pune centroid) |
| `WEATHER_CACHE_TTL_SECONDS` | int | `900` | In-memory spatial cache expiration time (15 minutes) |
| `WEATHER_CACHE_GRID_DECIMALS`| int | `2` | Spatial coordinate quantization resolution (2 decimals $\approx 1.1\text{ km}$) |
| `WEATHER_TIMEOUT_SECONDS` | float | `6.0` | HTTP request timeout for upstream weather API queries |
| `WEATHER_MAX_RETRIES` | int | `3` | Maximum retry attempts for transient upstream network errors |
| `WEATHER_PERSIST_DEFAULT` | bool | `false` | Automatically persist weather observations on retrieval |
| `IMD_API_TOKEN` | string | `""` | Optional access token for official IMD station data feeds |
| `IMD_API_BASE_URL` | string | `https://api.imd.gov.in/public/` | Base endpoint for IMD governmental services |

Sample `.env` configuration snippet:
```bash
# Weather Service Configuration
WEATHER_PROVIDER=open-meteo
WEATHER_DEFAULT_DISTRICT=pune
WEATHER_CACHE_TTL_SECONDS=900
WEATHER_TIMEOUT_SECONDS=6.0
WEATHER_MAX_RETRIES=3
WEATHER_PERSIST_DEFAULT=false
```

---

## 2. Provider Switching Protocol

The weather service uses the Strategy Pattern via `BaseWeatherProvider`. To switch providers or test offline baselines:

### 2.1 Standard Operation (Open-Meteo Primary + IMD Warnings)
By default, `WeatherService` initializes:
```python
self.primary_provider = OpenMeteoProvider()
self.alert_provider = IMDWeatherProvider()
```
This requires zero third-party API keys and operates with up to 10,000 requests per day under the CC-BY 4.0 license.

### 2.2 Offline / Testing Simulation Mode
When running automated integration tests or simulating rural disconnected operation:
```python
# Force regional baseline fallback
report = await weather_service.get_comprehensive_weather(
    district="kolhapur",
    force_refresh=True
)
```
If Open-Meteo is unreachable, the orchestrator automatically invokes `_build_fallback_weather()`, constructing a high-fidelity synthetic baseline representing Western Maharashtra sugarcane microclimates ($28.5^\circ\text{C}$, $65\%\text{ RH}$, $8.0\text{ km/h wind}$, $0.0\text{ mm rain}$).

---

## 3. Cache Tuning & Performance Optimization

To protect upstream providers and deliver sub-20ms dashboard render speeds, the spatial cache operates with coordinate quantization:

```python
# Quantization formula
grid_lat = round(latitude, 2)   # e.g., 18.5204 -> 18.52
grid_lon = round(longitude, 2)  # e.g., 73.8567 -> 73.86
cache_key = f"weather_comp:{grid_lat}:{grid_lon}"
```

### Tuning Recommendations:
- **High-traffic production:** Set `WEATHER_CACHE_TTL_SECONDS=1800` (30 minutes). Atmospheric conditions rarely change significantly within 30 minutes in agricultural zones.
- **Storm / Monsoon tracking:** Set `WEATHER_CACHE_TTL_SECONDS=600` (10 minutes) for faster tracking of rapidly moving rain cells.

---

## 4. Troubleshooting Guide

### 4.1 Upstream Rate Limiting (HTTP 429)
- **Symptom:** Upstream server returns status 429.
- **Handling:** `OpenMeteoProvider._get_with_retry` automatically applies exponential backoff ($0.5\text{s} \to 1.0\text{s} \to 2.0\text{s}$). If all retries fail, `WeatherService` activates the regional baseline fallback and tags the response with `data_source="fallback"`.
- **Resolution:** Verify that `weather_cache` is enabled so repetitive client polling hits memory rather than upstream servers.

### 4.2 Upstream Archive Overload (HTTP 503)
- **Symptom:** Open-Meteo Historical Archive API returns `503 Service Unavailable: The service is overloaded`.
- **Handling:** `fetch_historical` catches the exception and returns a structured regional reanalysis baseline with `is_fallback: true` instead of bubbling an HTTP 500 error to the client.

### 4.3 Out of Bounds Coordinate Error (HTTP 400)
- **Symptom:** Client receives `400 Bad Request: Latitude out of bounds`.
- **Handling:** `validate_coordinates` checks that $-90.0 \le \text{lat} \le 90.0$ and $-180.0 \le \text{lon} \le 180.0$.
- **Resolution:** Ensure the client passes standard WGS84 decimal degrees.

### 4.4 Verifying Database Persistence
To verify that observations are saving to the relational database:
```python
from app.db.session import SessionLocal
from app.models.weather_history import WeatherObservation

db = SessionLocal()
latest = db.query(WeatherObservation).order_by(WeatherObservation.id.desc()).first()
print(f"Latest observation: {latest.location_name} | {latest.temperature}°C | {latest.spray_suitability}")
db.close()
```

