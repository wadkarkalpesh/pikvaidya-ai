"""
Production Readiness & Infrastructure Test Suite
================================================
Validates that containerization assets, environment configs, model registries,
and deployment entrypoints adhere strictly to production enterprise standards.
"""

from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.model_service import model_service
from app.services.segmentation_service import segmentation_service

client = TestClient(app)


def test_production_containerization_assets_exist():
    """Verify that all essential deployment and containerization files exist."""
    project_root = Path(__file__).resolve().parent.parent.parent
    
    dockerfile = project_root / "Dockerfile"
    docker_compose = project_root / "docker-compose.yml"
    dockerignore = project_root / ".dockerignore"
    env_example = project_root / ".env.production.example"
    run_ps1 = project_root / "scripts" / "run_production.ps1"
    run_sh = project_root / "scripts" / "run_production.sh"

    assert dockerfile.exists(), "Dockerfile must exist at repository root"
    assert docker_compose.exists(), "docker-compose.yml must exist at repository root"
    assert dockerignore.exists(), ".dockerignore must exist at repository root"
    assert env_example.exists(), ".env.production.example must exist at repository root"
    assert run_ps1.exists(), "scripts/run_production.ps1 must exist"
    assert run_sh.exists(), "scripts/run_production.sh must exist"

    # Validate Dockerfile contents
    dockerfile_content = dockerfile.read_text(encoding="utf-8")
    assert "node:20-alpine" in dockerfile_content
    assert "python:3.11-slim" in dockerfile_content
    assert "HEALTHCHECK" in dockerfile_content


def test_settings_production_compliance():
    """Verify configuration settings adhere to production specifications."""
    assert settings.PROJECT_NAME == "PikVaidya AI"
    assert settings.VERSION is not None
    assert settings.API_V1_STR == "/api/v1"
    assert settings.UPLOAD_DIR is not None
    assert settings.MAX_UPLOAD_SIZE_MB > 0


def test_health_telemetry_live():
    """Verify that the production health check endpoint returns 200 with service info."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "PikVaidya AI"


def test_multi_crop_model_registry_production_integrity():
    """Verify sugarcane, tomato, and onion models can be loaded and cached in production."""
    for crop in ["sugarcane", "tomato", "onion"]:
        model_service.load_model(crop=crop)
        assert crop in model_service.crop_models, f"Model entry missing for {crop}"
        crop_data = model_service.crop_models[crop]
        assert crop_data["model"] is not None
        assert "idx_to_class" in crop_data
        assert len(crop_data["idx_to_class"]) in [4, 5, 10], f"Unexpected class count for {crop}"


def test_uploads_directory_is_writable():
    """Verify the uploads directory can be written to and read from in production."""
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    test_probe = upload_dir / "probe_readiness.tmp"
    try:
        test_probe.write_text("probe_ok", encoding="utf-8")
        assert test_probe.read_text(encoding="utf-8") == "probe_ok"
    finally:
        if test_probe.exists():
            test_probe.unlink()
