"""
Phase 8: Offline Progressive Web App (PWA), IndexedDB Caching & Edge Quantization Tests
========================================================================================
Validates:
1. Model static endpoint availability and file sizes
2. ONNX INT8 model graph integrity and tensor shapes
3. Offline sync protocol with idempotency and historical capture timestamps
4. Frontend PWA manifest and service worker generation
"""

import os
import io
import pytest
import onnx
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_leaf_image_bytes():
    """Generates synthetic RGB leaf image for integration testing."""
    img = Image.new("RGB", (224, 224), color=(34, 139, 34))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.getvalue()


class TestPhase8EdgeModels:
    """Verifies edge quantized INT8 models and their serving endpoints."""

    @pytest.mark.parametrize("crop,filename,expected_classes", [
        ("sugarcane", "sugarcane_mobilenetv3_int8.onnx", 5),
        ("tomato", "tomato_mobilenetv3_int8.onnx", 10),
        ("onion", "onion_mobilenetv3_large_int8.onnx", 4),
    ])
    def test_model_files_exist_and_valid_onnx(self, crop, filename, expected_classes):
        path = os.path.join("models", filename)
        assert os.path.exists(path), f"Quantized model file missing: {path}"
        assert os.path.getsize(path) > 10 * 1024 * 1024, f"Model file too small: {path}"

        # Load ONNX graph and verify structure
        model = onnx.load(path)
        onnx.checker.check_model(model)

        # Verify input tensor
        inp = model.graph.input[0]
        assert inp.name == "input"
        in_dims = [d.dim_value for d in inp.type.tensor_type.shape.dim]
        assert in_dims[1:] == [3, 224, 224]

        # Verify output tensor
        out = model.graph.output[0]
        assert out.name == "output"
        out_dims = [d.dim_value for d in out.type.tensor_type.shape.dim]
        assert out_dims[1] == expected_classes

    def test_models_static_route_serving(self, client):
        """Tests that models can be downloaded via HTTP GET for client browser caching."""
        for filename in [
            "sugarcane_mobilenetv3_int8.onnx",
            "tomato_mobilenetv3_int8.onnx",
            "onion_mobilenetv3_large_int8.onnx"
        ]:
            response = client.get(f"/models/{filename}")
            assert response.status_code == 200, f"Failed to serve /models/{filename}"
            # Check content length header or body
            assert len(response.content) > 10 * 1024 * 1024


class TestPhase8OfflineSyncProtocol:
    """Verifies background synchronization and idempotency."""

    def test_offline_sync_submission(self, client, sample_leaf_image_bytes):
        """Tests syncing a leaf scan captured offline with metadata."""
        idempotency_key = "test_idem_phase8_sync_001"
        response = client.post(
            "/api/crop-health/predict",
            files={"file": ("offline_leaf.jpg", sample_leaf_image_bytes, "image/jpeg")},
            data={
                "crop": "sugarcane",
                "district": "Pune",
                "captured_at": "2026-11-10T10:30:00Z",
                "idempotency_key": idempotency_key,
                "is_offline_synced": "true"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "predicted_class" in data or "predicted_disease" in data
        assert "model_confidence" in data or "confidence" in data
        assert data.get("crop_type") == "sugarcane" or data.get("crop") == "sugarcane"
        assert data.get("is_offline_synced") is True or data.get("is_offline_synced") == "true"

    def test_idempotent_duplicate_submission(self, client, sample_leaf_image_bytes):
        """Tests submitting the identical idempotency key twice succeeds cleanly."""
        idempotency_key = "test_idem_duplicate_key_002"
        # First submission
        res1 = client.post(
            "/api/crop-health/predict",
            files={"file": ("offline_leaf.jpg", sample_leaf_image_bytes, "image/jpeg")},
            data={
                "crop": "tomato",
                "district": "Nashik",
                "captured_at": "2026-11-10T10:35:00Z",
                "idempotency_key": idempotency_key,
                "is_offline_synced": "true"
            }
        )
        assert res1.status_code == 200

        # Second submission (network re-try simulation)
        res2 = client.post(
            "/api/crop-health/predict",
            files={"file": ("offline_leaf.jpg", sample_leaf_image_bytes, "image/jpeg")},
            data={
                "crop": "tomato",
                "district": "Nashik",
                "captured_at": "2026-11-10T10:35:00Z",
                "idempotency_key": idempotency_key,
                "is_offline_synced": "true"
            }
        )
        assert res2.status_code == 200


class TestPhase8PWAArtifacts:
    """Verifies production PWA service worker and Web App Manifest build artifacts."""

    def test_pwa_dist_files_exist(self):
        dist_dir = os.path.join("frontend", "dist")
        assert os.path.exists(dist_dir), "frontend/dist not found"

        sw_path = os.path.join(dist_dir, "sw.js")
        manifest_path = os.path.join(dist_dir, "manifest.webmanifest")

        assert os.path.exists(sw_path), "Service worker sw.js missing in dist"
        assert os.path.exists(manifest_path), "manifest.webmanifest missing in dist"

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_content = f.read()
            assert "PikVaidya" in manifest_content
            assert "standalone" in manifest_content
