"""
PikVaidya AI — Automated Test Suite for IoT In-Situ Sensor Telemetry Feed
=========================================================================
Tests device registration, token authentication, hardware sensor ingestion,
LoRaWAN webhook parsing, in-situ epidemiological risks, and multi-tool integration.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.dependencies import get_db, get_current_active_user
from app.models.user import User, UserRole
from app.models.farm import Farm
from app.models.iot_device import IoTDevice
from app.models.iot_telemetry import IoTTelemetry
from app.schemas.iot import IoTDeviceCreate, IoTTelemetryIngest, LoRaWANUplinkPayload
from app.services.iot_service import iot_service


# ------------------------------------------------------------------------------
# Test Fixtures & Database Setup
# ------------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def test_user(db_session):
    user = User(
        id=1,
        name="Balaram Patil",
        email="balaram.patil@example.com",
        password_hash="fake_hash_value_123",
        preferred_language="mr",
        role=UserRole.FARMER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_farm(db_session, test_user):
    farm = Farm(
        id=10,
        user_id=test_user.id,
        name="Kolhapur Cane Estate #1",
        area=4.5,
        soil_type="Deep Black Clay",
        irrigation="Drip",
        latitude=16.7050,
        longitude=74.2433,
    )
    db_session.add(farm)
    db_session.commit()
    db_session.refresh(farm)
    return farm


@pytest.fixture(scope="function")
def client(db_session, test_user):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ------------------------------------------------------------------------------
# Unit & Integration Tests
# ------------------------------------------------------------------------------

def test_device_registration_and_token_generation(db_session, test_user, test_farm):
    """Verifies physical IoT node registration, SHA-256 key hashing, and farm association."""
    data = IoTDeviceCreate(
        device_id="NODE-KOLHAPUR-001",
        device_name="Cane Canopy Node North",
        farm_id=test_farm.id,
        device_type="CANOPY_MONITOR",
        hardware_model="ESP32-S3-LoRaWAN-v2",
        firmware_version="2.1.0",
        latitude=16.7052,
        longitude=74.2435,
    )

    device, raw_key = iot_service.register_device(db=db_session, user=test_user, data=data)

    assert device.id is not None
    assert device.device_id == "NODE-KOLHAPUR-001"
    assert device.farm_id == test_farm.id
    assert raw_key.startswith("pviot_")
    # Verify raw key is not stored in plaintext
    assert device.api_key_hash != raw_key
    assert device.api_key_hash == iot_service.hash_token(raw_key)


def test_device_token_authentication(db_session, test_user, test_farm):
    """Verifies cryptographic token verification and unauthorized rejections."""
    data = IoTDeviceCreate(
        device_id="NODE-AUTH-TEST",
        device_name="Auth Test Station",
        farm_id=test_farm.id,
    )
    device, raw_key = iot_service.register_device(db=db_session, user=test_user, data=data)

    # Valid token succeeds
    authenticated = iot_service.authenticate_device(db=db_session, token=raw_key)
    assert authenticated.device_id == "NODE-AUTH-TEST"

    # Explicit device_id matching succeeds
    auth_with_id = iot_service.authenticate_device(db=db_session, token=raw_key, device_id="NODE-AUTH-TEST")
    assert auth_with_id.device_id == "NODE-AUTH-TEST"

    # Invalid token fails with 401
    with pytest.raises(Exception) as exc:
        iot_service.authenticate_device(db=db_session, token="invalid_key_12345")
    assert "401" in str(exc.value)


def test_direct_telemetry_ingestion_and_risk_evaluation(db_session, test_user, test_farm):
    """Verifies direct hardware sensor ingest, bounds validation, and instant in-situ risk calculation."""
    device, raw_key = iot_service.register_device(
        db=db_session,
        user=test_user,
        data=IoTDeviceCreate(
            device_id="STATION-PUNE-SOIL",
            device_name="Tomato Weather Station",
            farm_id=test_farm.id,
        )
    )

    # Case 1: Optimal weather, no rain, dry leaves -> Spray safe, low fungal risk
    payload_safe = IoTTelemetryIngest(
        ambient_temperature_c=26.5,
        ambient_humidity_pct=62.0,
        canopy_temperature_c=25.8,
        canopy_humidity_pct=65.0,
        leaf_wetness_minutes=0,
        leaf_wetness_active=False,
        soil_moisture_10cm_pct=34.5,
        wind_speed_2m_kmh=8.2,
        solar_radiation_wm2=650.0,
        battery_level_pct=94.0,
        battery_voltage_v=4.12,
        signal_rssi=-78,
    )

    t1 = iot_service.ingest_telemetry(db=db_session, device=device, data=payload_safe)
    assert t1.id is not None
    assert t1.spray_window_safe is True
    assert t1.fungal_conduciveness_score < 0.50
    assert device.status == "ACTIVE"
    assert device.battery_level_pct == 94.0

    # Case 2: High wind (> 15 km/h) & wet foliage -> Spray unsafe, high fungal risk
    payload_unsafe = IoTTelemetryIngest(
        ambient_temperature_c=24.0,
        ambient_humidity_pct=88.0,
        leaf_wetness_minutes=45,
        leaf_wetness_active=True,
        rainfall_rate_mmh=1.2,
        wind_speed_2m_kmh=18.5,
    )
    t2 = iot_service.ingest_telemetry(db=db_session, device=device, data=payload_unsafe)
    assert t2.spray_window_safe is False
    assert t2.fungal_conduciveness_score >= 0.70


def test_lorawan_webhook_payload_parsing(db_session, test_user, test_farm):
    """Verifies LoRaWAN uplink ingestion conforming to TTN and ChirpStack webhook specs."""
    dev_id = "0004A30B001F9999"
    device, _ = iot_service.register_device(
        db=db_session,
        user=test_user,
        data=IoTDeviceCreate(
            device_id=dev_id,
            device_name="LoRaWAN Onion Node",
            farm_id=test_farm.id,
        )
    )

    ttn_payload = LoRaWANUplinkPayload(
        end_device_ids={"device_id": dev_id, "dev_eui": dev_id},
        decoded_payload={
            "temperature": 27.2,
            "humidity": 78.5,
            "leaf_wetness_minutes": 25,
            "soil_moisture": 42.0,
            "wind_speed": 6.4,
            "battery": 88.0,
            "rssi": -85,
        }
    )

    telemetry = iot_service.decode_lorawan_uplink(db=db_session, payload=ttn_payload)
    assert telemetry.device_id == dev_id
    assert telemetry.ambient_temperature_c == 27.2
    assert telemetry.ambient_humidity_pct == 78.5
    assert telemetry.leaf_wetness_minutes == 25
    assert telemetry.soil_moisture_10cm_pct == 42.0


def test_farm_telemetry_history_and_summary(db_session, test_user, test_farm):
    """Verifies retrieval of latest observations, time-series history, and 24h rolling agronomic summary."""
    device, _ = iot_service.register_device(
        db=db_session,
        user=test_user,
        data=IoTDeviceCreate(
            device_id="HISTORY-TEST-NODE",
            device_name="Sugarcane In-Situ Station",
            farm_id=test_farm.id,
        )
    )

    base_time = datetime.now(timezone.utc)
    for i in range(5):
        reading = IoTTelemetryIngest(
            ambient_temperature_c=25.0 + i,
            ambient_humidity_pct=70.0 + i,
            leaf_wetness_minutes=15,
            rainfall_rate_mmh=0.5,
            wind_speed_2m_kmh=10.0,
            timestamp=base_time - timedelta(hours=i),
        )
        iot_service.ingest_telemetry(db=db_session, device=device, data=reading)

    latest = iot_service.get_latest_farm_telemetry(db_session, test_farm.id)
    assert latest is not None
    assert latest.ambient_temperature_c == 25.0

    history = iot_service.get_farm_telemetry_history(db_session, test_farm.id, hours=12)
    assert len(history) == 5

    summary = iot_service.get_farm_iot_summary(db_session, test_farm.id)
    assert summary is not None
    assert summary.farm_id == test_farm.id
    assert summary.is_live is True
    assert summary.leaf_wetness_hours_last_24h > 0
    assert summary.total_rainfall_last_24h_mm > 0


def test_iot_api_endpoints_via_client(client, db_session, test_farm):
    """Verifies REST endpoints for registering devices, querying devices, and ingesting telemetry."""
    # 1. Register device via POST /api/v1/iot/devices
    reg_res = client.post(
        "/api/v1/iot/devices",
        json={
            "device_id": "REST-NODE-101",
            "device_name": "Nashik Field Sensor",
            "farm_id": test_farm.id,
            "device_type": "WEATHER_STATION",
        }
    )
    assert reg_res.status_code == 201
    reg_json = reg_res.json()
    assert reg_json["device_id"] == "REST-NODE-101"
    raw_key = reg_json["api_key"]
    assert raw_key is not None

    # 2. Ingest telemetry via POST /api/v1/iot/telemetry using X-Device-Token
    tele_res = client.post(
        "/api/v1/iot/telemetry",
        headers={"X-Device-Token": raw_key},
        json={
            "ambient_temperature_c": 28.5,
            "ambient_humidity_pct": 72.0,
            "canopy_temperature_c": 27.9,
            "leaf_wetness_minutes": 10,
            "wind_speed_2m_kmh": 9.5,
        }
    )
    assert tele_res.status_code == 201
    tele_json = tele_res.json()
    assert tele_json["ambient_temperature_c"] == 28.5
    assert tele_json["device_id"] == "REST-NODE-101"

    # 3. Retrieve latest farm observation via GET /api/v1/iot/farms/{farm_id}/latest
    latest_res = client.get(f"/api/v1/iot/farms/{test_farm.id}/latest")
    assert latest_res.status_code == 200
    assert latest_res.json()["ambient_temperature_c"] == 28.5

    # 4. Retrieve farm summary via GET /api/v1/iot/farms/{farm_id}/summary
    summary_res = client.get(f"/api/v1/iot/farms/{test_farm.id}/summary")
    assert summary_res.status_code == 200
    sum_json = summary_res.json()
    assert sum_json["device_id"] == "REST-NODE-101"
    assert sum_json["is_live"] is True


def test_orchestrator_insitu_integration(db_session, test_user, test_farm):
    """Verifies that the RAG LLM orchestrator automatically prioritizes live in-situ IoT telemetry."""
    import asyncio
    from app.services.rag.orchestrator import llm_orchestrator
    from app.schemas.assistant import MultimodalChatRequest

    # Create active IoT node and ingest fresh reading
    device, _ = iot_service.register_device(
        db=db_session,
        user=test_user,
        data=IoTDeviceCreate(
            device_id="ORCH-IOT-NODE",
            device_name="Orchestrator Integrated Node",
            farm_id=test_farm.id,
        )
    )

    iot_service.ingest_telemetry(
        db=db_session,
        device=device,
        data=IoTTelemetryIngest(
            ambient_temperature_c=29.2,
            ambient_humidity_pct=84.0,
            leaf_wetness_minutes=35,
            leaf_wetness_active=True,
            wind_speed_2m_kmh=12.0,
        )
    )

    req = MultimodalChatRequest(
        message="हवामान कसे आहे आणि आज फवारणी करावी का?",
        farm_id=test_farm.id,
        crop="sugarcane",
        language="mr",
    )

    response = asyncio.run(llm_orchestrator.orchestrate(request=req, db=db_session))
    assert response is not None
    # Verify weather tool trace reflects in-situ node
    weather_trace = next((t for t in response.tools_invoked if t.tool_name == "weather_risk_tool"), None)
    assert weather_trace is not None
    assert "In-Situ IoT Node" in weather_trace.summary
    assert "Leaf Wetness" in weather_trace.summary
