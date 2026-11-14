"""
PikVaidya AI — IoT Telemetry & Microclimate Ingestion Service
=============================================================
Manages physical in-situ agricultural IoT devices, cryptographic token validation,
sensor range checks, LoRaWAN / MQTT payload decoders, and real-time in-situ disease risk.
"""

import hashlib
import json
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.iot_device import IoTDevice
from app.models.iot_telemetry import IoTTelemetry
from app.models.farm import Farm
from app.models.user import User, UserRole
from app.schemas.iot import (
    IoTDeviceCreate,
    IoTDeviceUpdate,
    IoTTelemetryIngest,
    LoRaWANUplinkPayload,
    IoTTelemetrySummary,
)

logger = logging.getLogger(__name__)


class IoTService:
    """Enterprise service orchestrator for physical agricultural sensor telemetries."""

    @staticmethod
    def hash_token(token: str) -> str:
        """Computes SHA-256 hash of device token for tamper-proof storage."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def generate_device_key(self) -> Tuple[str, str]:
        """Generates a high-entropy 256-bit device secret token and its SHA-256 hash."""
        raw_token = f"pviot_{secrets.token_urlsafe(32)}"
        return raw_token, self.hash_token(raw_token)

    def register_device(
        self,
        db: Session,
        user: User,
        data: IoTDeviceCreate,
    ) -> Tuple[IoTDevice, str]:
        """Registers a new in-situ sensor node on an agricultural farm parcel."""
        # 1. Check for device_id uniqueness
        existing = db.query(IoTDevice).filter(IoTDevice.device_id == data.device_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Device identifier '{data.device_id}' is already registered."
            )

        # 2. Verify farm ownership if farm_id specified
        if data.farm_id is not None:
            farm = db.query(Farm).filter(Farm.id == data.farm_id).first()
            if not farm:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Farm ID {data.farm_id} does not exist."
                )
            if farm.user_id != user.id and user.role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot register IoT device for a farm owned by another user."
                )

        # 3. Generate cryptographic API key
        raw_key, key_hash = self.generate_device_key()

        device = IoTDevice(
            device_id=data.device_id,
            device_name=data.device_name,
            farm_id=data.farm_id,
            device_type=data.device_type,
            hardware_model=data.hardware_model,
            firmware_version=data.firmware_version,
            api_key_hash=key_hash,
            status="ACTIVE",
            latitude=data.latitude,
            longitude=data.longitude,
            altitude_m=data.altitude_m,
        )

        db.add(device)
        db.commit()
        db.refresh(device)
        logger.info("Successfully registered IoT device %s for farm %s", device.device_id, device.farm_id)
        return device, raw_key

    def authenticate_device(
        self,
        db: Session,
        token: str,
        device_id: Optional[str] = None,
    ) -> IoTDevice:
        """Validates incoming device token and returns authenticated device entity."""
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing device authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        key_hash = self.hash_token(token)
        query = db.query(IoTDevice).filter(IoTDevice.api_key_hash == key_hash)
        if device_id:
            query = query.filter(IoTDevice.device_id == device_id)

        device = query.first()
        if not device:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or unauthorized IoT device token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if device.status == "DECOMMISSIONED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This device has been decommissioned and cannot ingest telemetry."
            )

        return device

    def evaluate_in_situ_risks(
        self,
        data: IoTTelemetryIngest,
    ) -> Dict[str, Any]:
        """
        Computes real-time agronomic risk indices from physical in-situ sensor data:
        1. Spray Window Safety: checks wind at canopy (2m), rain rate, leaf moisture, and heat.
        2. Fungal Spore Conduciveness: evaluated from actual leaf wetness minutes + temperature.
        3. Physiological Stress: Frost and extreme heat.
        """
        temp = data.canopy_temperature_c if data.canopy_temperature_c is not None else data.ambient_temperature_c
        rh = data.canopy_humidity_pct if data.canopy_humidity_pct is not None else data.ambient_humidity_pct

        # 1. Spray Window Gating
        is_wind_excessive = data.wind_speed_2m_kmh > 15.0 or (data.wind_gust_kmh and data.wind_gust_kmh > 22.0)
        is_raining = data.rainfall_rate_mmh > 0.4
        is_humidity_extreme = rh > 92.0
        is_heat_extreme = temp > 35.0
        is_foliage_wet = data.leaf_wetness_active or data.leaf_wetness_minutes >= 15

        spray_safe = not (is_wind_excessive or is_raining or is_humidity_extreme or is_heat_extreme or is_foliage_wet)

        # 2. In-Situ Fungal Conduciveness Score (0.0 to 1.0)
        # Wet leaf surface + warm temperature (18-28C) creates optimal infection window
        fungal_score = 0.0
        if rh >= 85.0:
            fungal_score += 0.35
        elif rh >= 70.0:
            fungal_score += 0.20

        if 18.0 <= temp <= 28.0:
            fungal_score += 0.30
        elif 14.0 <= temp <= 32.0:
            fungal_score += 0.15

        if data.leaf_wetness_active:
            fungal_score += 0.35
        elif data.leaf_wetness_minutes > 0:
            fungal_score += min(0.35, (data.leaf_wetness_minutes / 60.0) * 0.35)

        fungal_score = min(1.0, round(fungal_score, 3))

        # 3. Environmental Stresses
        frost_risk = temp <= 3.5
        heat_risk = temp >= 38.0

        return {
            "spray_window_safe": spray_safe,
            "fungal_conduciveness_score": fungal_score,
            "frost_risk": frost_risk,
            "heat_stress_risk": heat_risk,
        }

    def ingest_telemetry(
        self,
        db: Session,
        device: IoTDevice,
        data: IoTTelemetryIngest,
        raw_payload: Optional[str] = None,
    ) -> IoTTelemetry:
        """Validates, computes agronomic indices, and persists live in-situ telemetry."""
        obs_time = data.timestamp or datetime.now(timezone.utc)
        risks = self.evaluate_in_situ_risks(data)

        telemetry = IoTTelemetry(
            device_id=device.device_id,
            farm_id=device.farm_id,
            timestamp=obs_time,
            ambient_temperature_c=data.ambient_temperature_c,
            ambient_humidity_pct=data.ambient_humidity_pct,
            canopy_temperature_c=data.canopy_temperature_c,
            canopy_humidity_pct=data.canopy_humidity_pct,
            leaf_wetness_minutes=data.leaf_wetness_minutes,
            leaf_wetness_active=data.leaf_wetness_active,
            soil_moisture_10cm_pct=data.soil_moisture_10cm_pct,
            soil_moisture_30cm_pct=data.soil_moisture_30cm_pct,
            soil_temperature_c=data.soil_temperature_c,
            rainfall_rate_mmh=data.rainfall_rate_mmh,
            rainfall_cumulative_mm=data.rainfall_cumulative_mm,
            wind_speed_2m_kmh=data.wind_speed_2m_kmh,
            wind_gust_kmh=data.wind_gust_kmh,
            solar_radiation_wm2=data.solar_radiation_wm2,
            atmospheric_pressure_hpa=data.atmospheric_pressure_hpa,
            spray_window_safe=risks["spray_window_safe"],
            fungal_conduciveness_score=risks["fungal_conduciveness_score"],
            frost_risk=risks["frost_risk"],
            heat_stress_risk=risks["heat_stress_risk"],
            battery_level_pct=data.battery_level_pct,
            battery_voltage_v=data.battery_voltage_v,
            signal_rssi=data.signal_rssi,
            raw_payload=raw_payload,
        )

        db.add(telemetry)

        # Update Device Live Status
        device.last_telemetry_at = obs_time
        device.status = "ACTIVE"
        if data.battery_level_pct is not None:
            device.battery_level_pct = data.battery_level_pct
        if data.battery_voltage_v is not None:
            device.battery_voltage_v = data.battery_voltage_v
        if data.signal_rssi is not None:
            device.signal_rssi = data.signal_rssi

        db.commit()
        db.refresh(telemetry)
        return telemetry

    def decode_lorawan_uplink(
        self,
        db: Session,
        payload: LoRaWANUplinkPayload,
    ) -> IoTTelemetry:
        """
        Parses LoRaWAN webhook uplinks (ChirpStack v4 or The Things Network v3),
        extracts DevEUI/device_id, decodes sensor payload, and persists telemetry.
        """
        # Resolve device ID from standard LoRaWAN payloads
        dev_id = None
        if payload.end_device_ids:
            dev_id = (
                payload.end_device_ids.get("device_id")
                or payload.end_device_ids.get("dev_eui")
            )
        dev_id = dev_id or payload.device_id or payload.dev_eui

        if not dev_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract device_id or dev_eui from LoRaWAN payload."
            )

        device = db.query(IoTDevice).filter(IoTDevice.device_id == dev_id).first()
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"LoRaWAN node with DevEUI/ID '{dev_id}' is not registered."
            )

        # Extract telemetry fields from decoded_payload
        decoded = payload.decoded_payload
        if not decoded and payload.uplink_message:
            decoded = payload.uplink_message.get("decoded_payload")

        if not decoded:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LoRaWAN payload does not contain decoded_payload fields. Please enable payload codec on gateway."
            )

        # Map common IoT payload keys (supports standard Cayenne LPP and custom agricultural frames)
        temp = float(decoded.get("temperature") or decoded.get("ambient_temperature_c") or decoded.get("temp") or 25.0)
        humidity = float(decoded.get("humidity") or decoded.get("ambient_humidity_pct") or decoded.get("rh") or 60.0)

        ingest_data = IoTTelemetryIngest(
            ambient_temperature_c=temp,
            ambient_humidity_pct=humidity,
            canopy_temperature_c=decoded.get("canopy_temperature_c") or decoded.get("canopy_temp"),
            canopy_humidity_pct=decoded.get("canopy_humidity_pct") or decoded.get("canopy_rh"),
            leaf_wetness_minutes=int(decoded.get("leaf_wetness_minutes") or decoded.get("wetness_min") or 0),
            leaf_wetness_active=bool(decoded.get("leaf_wetness_active") or decoded.get("wetness_active") or False),
            soil_moisture_10cm_pct=decoded.get("soil_moisture_10cm_pct") or decoded.get("soil_10cm") or decoded.get("soil_moisture"),
            soil_moisture_30cm_pct=decoded.get("soil_moisture_30cm_pct") or decoded.get("soil_30cm"),
            rainfall_rate_mmh=float(decoded.get("rainfall_rate_mmh") or decoded.get("rain_rate") or 0.0),
            rainfall_cumulative_mm=float(decoded.get("rainfall_cumulative_mm") or decoded.get("rain_accum") or 0.0),
            wind_speed_2m_kmh=float(decoded.get("wind_speed_2m_kmh") or decoded.get("wind_speed") or 0.0),
            solar_radiation_wm2=decoded.get("solar_radiation_wm2") or decoded.get("solar"),
            battery_level_pct=decoded.get("battery_level_pct") or decoded.get("battery"),
            battery_voltage_v=decoded.get("battery_voltage_v") or decoded.get("vbat"),
            signal_rssi=decoded.get("signal_rssi") or decoded.get("rssi"),
        )

        raw_str = json.dumps(payload.model_dump())
        return self.ingest_telemetry(db=db, device=device, data=ingest_data, raw_payload=raw_str)

    def get_latest_farm_telemetry(
        self,
        db: Session,
        farm_id: int,
    ) -> Optional[IoTTelemetry]:
        """Retrieves the most recent telemetry observation recorded for an agricultural farm."""
        return (
            db.query(IoTTelemetry)
            .filter(IoTTelemetry.farm_id == farm_id)
            .order_by(desc(IoTTelemetry.timestamp))
            .first()
        )

    def get_farm_telemetry_history(
        self,
        db: Session,
        farm_id: int,
        hours: int = 24,
    ) -> List[IoTTelemetry]:
        """Retrieves time-series telemetry series for a farm within the specified backward window."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return (
            db.query(IoTTelemetry)
            .filter(
                IoTTelemetry.farm_id == farm_id,
                IoTTelemetry.timestamp >= cutoff,
            )
            .order_by(IoTTelemetry.timestamp.asc())
            .all()
        )

    def get_farm_iot_summary(
        self,
        db: Session,
        farm_id: int,
    ) -> Optional[IoTTelemetrySummary]:
        """Computes live rolling 24-hour microclimate agronomic summary from in-situ sensors."""
        latest = self.get_latest_farm_telemetry(db, farm_id)
        if not latest:
            return None

        history = self.get_farm_telemetry_history(db, farm_id, hours=24)
        device = db.query(IoTDevice).filter(IoTDevice.device_id == latest.device_id).first()
        device_name = device.device_name if device else latest.device_id

        # Determine if reading is currently live (< 2 hours old)
        now_utc = datetime.now(timezone.utc)
        reading_ts = latest.timestamp
        if reading_ts.tzinfo is None:
            reading_ts = reading_ts.replace(tzinfo=timezone.utc)
        time_diff = (now_utc - reading_ts).total_seconds()
        is_live = time_diff <= 7200  # 2 hours

        # Aggregate rolling 24h metrics
        total_wetness_minutes = sum(t.leaf_wetness_minutes for t in history)
        leaf_wetness_hours = round(total_wetness_minutes / 60.0, 1)
        total_rain = sum(t.rainfall_rate_mmh for t in history)
        max_wind = max([t.wind_speed_2m_kmh for t in history] + [0.0])

        alerts: List[str] = []
        if latest.fungal_conduciveness_score >= 0.70:
            alerts.append(f"HIGH FUNGAL RISK: Sustained canopy wetness ({leaf_wetness_hours}h in 24h) and high humidity.")
        if not latest.spray_window_safe:
            alerts.append("SPRAY WINDOW UNSAFE: Unfavorable in-situ wind, wet foliage, or rain detected.")
        if latest.frost_risk:
            alerts.append("FROST ALERT: Canopy temperature dropped near freezing point.")
        if latest.heat_stress_risk:
            alerts.append("HEAT STRESS WARNING: Severe canopy temperature exceeding critical physiological limit.")

        risk_level = "CRITICAL" if latest.fungal_conduciveness_score >= 0.80 else ("HIGH" if latest.fungal_conduciveness_score >= 0.60 else ("MODERATE" if latest.fungal_conduciveness_score >= 0.35 else "LOW"))
        spray_status = "OPTIMAL_SAFE" if latest.spray_window_safe else "UNSAFE_CANCELLED"

        return IoTTelemetrySummary(
            farm_id=farm_id,
            device_id=latest.device_id,
            device_name=device_name,
            is_live=is_live,
            last_reading_at=latest.timestamp,
            current_temp_c=latest.ambient_temperature_c,
            current_humidity_pct=latest.ambient_humidity_pct,
            canopy_temp_c=latest.canopy_temperature_c,
            canopy_humidity_pct=latest.canopy_humidity_pct,
            current_soil_moisture_pct=latest.soil_moisture_10cm_pct,
            leaf_wetness_hours_last_24h=leaf_wetness_hours,
            total_rainfall_last_24h_mm=round(total_rain, 1),
            max_wind_speed_2m_kmh=round(max_wind, 1),
            spray_window_status=spray_status,
            fungal_spore_risk_level=risk_level,
            active_alerts=alerts,
        )


iot_service = IoTService()
