"""
Test Suite for Frontend Static Serving & SPA Mounting
Validates that the FastAPI backend correctly serves the compiled Vite React frontend,
assets, uploaded files, and system health endpoints.
"""

from fastapi.testclient import TestClient
from pathlib import Path
from app.main import app

client = TestClient(app)


def test_health_endpoint_still_returns_json():
    """Verify system health endpoint continues returning structured JSON."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data


def test_root_serves_spa_or_json():
    """Verify GET / returns either the SPA HTML (if dist exists) or system JSON."""
    response = client.get("/")
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    if "text/html" in content_type:
        assert "PikVaidya" in response.text
    else:
        data = response.json()
        assert "project" in data
        assert data["project"] == "PikVaidya AI"


def test_dashboard_route_serves_html():
    """Verify /dashboard route is accessible and serves HTML."""
    response = client.get("/dashboard/")
    # If compiled frontend exists, returns 200, otherwise 404
    frontend_dist = Path("frontend/dist")
    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "PikVaidya" in response.text
    else:
        assert response.status_code in [200, 404]


def test_uploads_mount_serves_files(tmp_path):
    """Verify /uploads endpoint can serve an uploaded test file."""
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    test_file = uploads_dir / "test_serving_beacon.txt"
    try:
        test_file.write_text("pikvaidya_serving_verified")
        response = client.get("/uploads/test_serving_beacon.txt")
        assert response.status_code == 200
        assert response.text == "pikvaidya_serving_verified"
    finally:
        if test_file.exists():
            test_file.unlink()

