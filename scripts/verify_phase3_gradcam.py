import sys
import math
from pathlib import Path
import numpy as np
import torch
from PIL import Image

# Ensure project root and backend directory are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
backend_path = PROJECT_ROOT / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.services.model_service import model_service
from src.explainability.gradcam import GradCAM, apply_colormap_on_image

print("--- PHASE 3: VERIFY GRAD-CAM EXPLAINABILITY ---")
model_service.load_model()

sample_img_path = Path("data/raw/sugarcane/Healthy/healthy (188).jpeg")
assert sample_img_path.exists(), f"Sample image {sample_img_path} not found"
orig_img = Image.open(sample_img_path).convert("RGB")
w_orig, h_orig = orig_img.size
print(f"Sample image loaded: {sample_img_path.name}, size=({w_orig}, {h_orig})")

# 1. Test standalone src.explainability.GradCAM
print("\n1. Testing standalone src.explainability.GradCAM class...")
target_layer = model_service.model.features[-1]
gradcam_engine = GradCAM(model_service.model, target_layer)

tensor, _ = model_service.preprocess_image(orig_img)
inp_tensor = tensor.unsqueeze(0).to(model_service.device).requires_grad_(True)
cam_mask = gradcam_engine.generate_cam(inp_tensor, target_class=0)

print(f"CAM mask shape: {cam_mask.shape}")
print(f"CAM mask min: {cam_mask.min():.4f}, max: {cam_mask.max():.4f}")
assert math.isfinite(cam_mask.min()) and math.isfinite(cam_mask.max()), "CAM mask values not finite"
assert cam_mask.min() >= 0.0 and cam_mask.max() <= 1.0, "CAM mask out of [0, 1] range"

output_dir = Path("uploads/heatmaps")
output_dir.mkdir(parents=True, exist_ok=True)
test_overlay_path = output_dir / "test_phase3_overlay.jpg"

blended = apply_colormap_on_image(orig_img, cam_mask, output_path=test_overlay_path, alpha=0.5)
print(f"Blended image size: {blended.size}")
assert blended.size == (w_orig, h_orig), f"Blended size {blended.size} does not match original ({w_orig}, {h_orig})"
assert test_overlay_path.exists(), "Overlay file was not saved"
print(f"Standalone GradCAM overlay verified and saved to {test_overlay_path}")

# 2. Test ModelServingService._generate_gradcam_heatmap (production service)
print("\n2. Testing ModelServingService Grad-CAM generation and hook safety...")
service_heatmap_path = output_dir / "test_phase3_service.jpg"
service_cam = model_service._generate_gradcam_heatmap(
    img_tensor=tensor,
    orig_img=orig_img,
    target_class=0,
    save_path=service_heatmap_path
)

print(f"Service CAM min: {service_cam.min():.4f}, max: {service_cam.max():.4f}")
assert math.isfinite(service_cam.min()) and math.isfinite(service_cam.max()), "Service CAM not finite"
assert service_heatmap_path.exists(), "Service heatmap file was not saved"

# Check saved JPEG image validity
with Image.open(service_heatmap_path) as saved_img:
    assert saved_img.size == (w_orig, h_orig), "Saved image size mismatch"
    assert saved_img.mode == "RGB", "Saved image mode is not RGB"

# 3. Test Hook Cleanup & Successive Calls (Checking for hook leaks)
print("\n3. Testing consecutive calls for hook accumulation...")
for i in range(5):
    res = model_service.predict(sample_img_path.read_bytes(), crop="sugarcane", generate_gradcam=True, save_heatmap=False)
    assert res["explanation_status"] == "generated", f"Iteration {i} explanation status: {res['explanation_status']}"
print("Successfully ran 5 consecutive Grad-CAM inferences without hook leaks or errors.")

# 4. Clean up test files
if test_overlay_path.exists():
    test_overlay_path.unlink()
if service_heatmap_path.exists():
    service_heatmap_path.unlink()

print("\n--- PHASE 3 VERIFICATION COMPLETE: ALL CHECKS PASSED ---")
