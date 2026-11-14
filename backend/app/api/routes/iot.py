"""
PikVaidya AI — IoT Telemetry & Sensor Gateway REST Endpoints
============================================================
Exposes REST and webhook endpoints for physical agricultural IoT devices,
LoRaWAN gateway integrations, time-series telemetry retrieval, and in-situ risk summaries.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_active_user
from app.models.user import User, UserRole
from app.models.iot_device import IoTDevice
from app.models.farm import Farm
from app.schemas.iot import (
    IoTDeviceCreate,
    IoTDeviceUpdate,
    IoTDeviceResponse,
    IoTTelemetryIngest,
    LoRaWANUplinkPayload,
    IoTTelemetryResponse,
    IoTTelemetrySummary,
)
from app.services.iot_service import iot_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/iot", tags=["IoT & In-Situ Farm Telemetry"])


# ------------------------------------------------------------------------------
# 1. IoT Device Management
# ------------------------------------------------------------------------------

@router.post(
    "/devices",
    response_model=IoTDeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new physical IoT sensor node",
    description="Registers an in-situ agricultural sensor station for a farm parcel and returns the raw secret API key.",
)
def register_iot_device(
    data: IoTDeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    device, raw_key = iot_service.register_device(db=db, user=current_user, data=data)
    response = IoTDeviceResponse.model_validate(device)
    response.api_key = raw_key
    return response


@router.get(
    "/devices",
    response_model=List[IoTDeviceResponse],
    summary="List registered IoT sensor nodes",
    description="Retrieves registered IoT sensor nodes, optionally filtered by farm ID.",
)
def list_iot_devices(
    farm_id: Optional[int] = Query(None, description="Optional farm ID filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(IoTDevice)
    if farm_id is not None:
        query = query.filter(IoTDevice.farm_id == farm_id)

    # If not admin, restrict to farms owned by current user
    if current_user.role != UserRole.ADMIN:
        user_farm_ids = [f.id for f in db.query(Farm.id).filter(Farm.user_id == current_user.id).all()]
        query = query.filter(IoTDevice.farm_id.in_(user_farm_ids))

    devices = query.order_by(IoTDevice.created_at.desc()).all()
    return devices


@router.get(
    "/devices/{device_id}",
    response_model=IoTDeviceResponse,
    summary="Get IoT device details",
)
def get_iot_device(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    device = db.query(IoTDevice).filter(IoTDevice.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IoT device not found.")

    if current_user.role != UserRole.ADMIN and device.farm_id:
        farm = db.query(Farm).filter(Farm.id == device.farm_id).first()
        if farm and farm.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this IoT device.")

    return device


@router.patch(
    "/devices/{device_id}",
    response_model=IoTDeviceResponse,
    summary="Update IoT device configuration",
)
def update_iot_device(
    device_id: str,
    data: IoTDeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    device = db.query(IoTDevice).filter(IoTDevice.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IoT device not found.")

    if current_user.role != UserRole.ADMIN and device.farm_id:
        farm = db.query(Farm).filter(Farm.id == device.farm_id).first()
        if farm and farm.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this IoT device.")

    if data.device_name is not None:
        device.device_name = data.device_name
    if data.farm_id is not None:
        device.farm_id = data.farm_id
    if data.status is not None:
        device.status = data.status
    if data.hardware_model is not None:
        device.hardware_model = data.hardware_model
    if data.firmware_version is not None:
        device.firmware_version = data.firmware_version
    if data.latitude is not None:
        device.latitude = data.latitude
    if data.longitude is not None:
        device.longitude = data.longitude

    db.commit()
    db.refresh(device)
    return device


@router.delete(
    "/devices/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Decommission or delete an IoT sensor node",
)
def delete_iot_device(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    device = db.query(IoTDevice).filter(IoTDevice.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IoT device not found.")

    if current_user.role != UserRole.ADMIN and device.farm_id:
        farm = db.query(Farm).filter(Farm.id == device.farm_id).first()
        if farm and farm.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this IoT device.")

    db.delete(device)
    db.commit()
    return None


# ------------------------------------------------------------------------------
# 2. Real-Time Telemetry Ingestion (Hardware Gateway)
# ------------------------------------------------------------------------------

@router.post(
    "/telemetry",
    response_model=IoTTelemetryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Direct sensor telemetry ingest endpoint",
    description="Accepts real-time atmospheric, canopy, soil, and leaf wetness observations from physical field devices.",
)
def ingest_iot_telemetry(
    payload: IoTTelemetryIngest,
    db: Session = Depends(get_db),
    x_device_token: Optional[str] = Header(None, description="Device secret API key in X-Device-Token header"),
    authorization: Optional[str] = Header(None, description="Device secret key in Authorization: Bearer <key>"),
    device_token: Optional[str] = Query(None, description="Device secret key passed as query parameter"),
    device_id: Optional[str] = Query(None, description="Optional device identifier for explicit binding"),
):
    # Extract token from header or query param
    token = x_device_token
    if not token and authorization:
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        else:
            token = authorization.strip()
    if not token:
        token = device_token

    device = iot_service.authenticate_device(db=db, token=token, device_id=device_id)
    telemetry = iot_service.ingest_telemetry(db=db, device=device, data=payload)
    return telemetry


@router.post(
    "/lorawan/uplink",
    response_model=IoTTelemetryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="LoRaWAN Webhook Ingest (ChirpStack / The Things Network)",
    description="Decodes uplink packets sent by LoRaWAN Network Servers and records in-situ farm telemetry.",
)
def ingest_lorawan_uplink(
    payload: LoRaWANUplinkPayload,
    db: Session = Depends(get_db),
    x_lorawan_secret: Optional[str] = Header(None, description="Optional LoRaWAN gateway secret"),
):
    telemetry = iot_service.decode_lorawan_uplink(db=db, payload=payload)
    return telemetry


# ------------------------------------------------------------------------------
# 3. Farm In-Situ Microclimate & Summary Queries
# ------------------------------------------------------------------------------

@router.get(
    "/farms/{farm_id}/latest",
    response_model=IoTTelemetryResponse,
    summary="Get latest in-situ telemetry observation for a farm",
)
def get_farm_latest_telemetry(
    farm_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found.")

    if current_user.role != UserRole.ADMIN and farm.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this farm.")

    latest = iot_service.get_latest_farm_telemetry(db, farm_id)
    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No in-situ IoT telemetry observations recorded for this farm."
        )
    return latest


@router.get(
    "/farms/{farm_id}/history",
    response_model=List[IoTTelemetryResponse],
    summary="Get historical telemetry time-series for a farm",
)
def get_farm_telemetry_history(
    farm_id: int,
    hours: int = Query(default=24, ge=1, le=720, description="Backward time window in hours (up to 30 days)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found.")

    if current_user.role != UserRole.ADMIN and farm.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this farm.")

    history = iot_service.get_farm_telemetry_history(db, farm_id, hours=hours)
    return history


@router.get(
    "/farms/{farm_id}/summary",
    response_model=IoTTelemetrySummary,
    summary="Get 24h rolling in-situ agronomic summary & spray risk",
)
def get_farm_iot_summary(
    farm_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found.")

    if current_user.role != UserRole.ADMIN and farm.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this farm.")

    summary = iot_service.get_farm_iot_summary(db, farm_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No in-situ IoT telemetry available to generate an agronomic summary for this farm."
        )
    return summary
