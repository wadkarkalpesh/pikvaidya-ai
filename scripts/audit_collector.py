#!/usr/bin/env python3
"""
PikVaidya AI — Automated Empirical Audit Collector
=================================================
Gathers exact, ground-truth technical evidence from the repository
to support the comprehensive technical report and audit documentation.
"""

import os
import sys
import json
import torch
from pathlib import Path

# Add project root and backend to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ["SECRET_KEY"] = "audit-secret-key-that-is-at-least-32-characters-long-valid!"
os.environ["ENVIRONMENT"] = "testing"

def audit_models():
    print("=== AUDITING MODEL CHECKPOINTS & METRICS ===")
    models_dir = PROJECT_ROOT / "models"
    models_data = {}

    for crop_dir in models_dir.iterdir():
        if not crop_dir.is_dir():
            continue
        crop_name = crop_dir.name
        models_data[crop_name] = {}
        for arch_dir in crop_dir.iterdir():
            if not arch_dir.is_dir():
                continue
            arch_name = arch_dir.name
            target_path = arch_dir
            if (arch_dir / "pipeline_trained").exists():
                target_path = arch_dir / "pipeline_trained"
            
            pth_file = target_path / "best_model.pth"
            onnx_file = arch_dir / "model.onnx"
            test_metrics_file = target_path / "test_metrics.json"
            calib_file = target_path / "calibration_metrics.json"
            cm_file = target_path / "confusion_matrix.csv"
            class_map_file = target_path / "class_mapping.json"
            
            entry = {
                "crop": crop_name,
                "architecture": arch_name,
                "path": str(target_path.relative_to(PROJECT_ROOT)),
                "pth_exists": pth_file.exists(),
                "pth_size_bytes": pth_file.stat().st_size if pth_file.exists() else 0,
                "onnx_exists": onnx_file.exists(),
                "onnx_size_bytes": onnx_file.stat().st_size if onnx_file.exists() else 0,
                "test_metrics": None,
                "calibration_metrics": None,
                "classes": None,
                "num_classes": 0,
                "param_count": 0,
            }
            
            if class_map_file.exists():
                with open(class_map_file, "r") as f:
                    entry["classes"] = json.load(f)
                    entry["num_classes"] = len(entry["classes"])
            
            if test_metrics_file.exists():
                with open(test_metrics_file, "r") as f:
                    entry["test_metrics"] = json.load(f)

            if calib_file.exists():
                with open(calib_file, "r") as f:
                    entry["calibration_metrics"] = json.load(f)

            # Inspect torch checkpoint if exists
            if pth_file.exists():
                try:
                    ckpt = torch.load(pth_file, map_location="cpu", weights_only=False)
                    if isinstance(ckpt, dict):
                        state_dict = None
                        if "model_state_dict" in ckpt:
                            state_dict = ckpt["model_state_dict"]
                        elif "state_dict" in ckpt:
                            state_dict = ckpt["state_dict"]
                        else:
                            state_dict = ckpt
                        
                        if isinstance(state_dict, dict):
                            entry["param_count"] = sum(p.numel() for p in state_dict.values() if hasattr(p, "numel"))
                        
                        if "metrics" in ckpt and not entry["test_metrics"]:
                            entry["test_metrics"] = ckpt["metrics"]
                        if "epoch" in ckpt:
                            entry["checkpoint_epoch"] = ckpt["epoch"]
                        if "temperature" in ckpt:
                            entry["checkpoint_temperature"] = ckpt["temperature"]
                    elif hasattr(ckpt, "parameters"):
                        entry["param_count"] = sum(p.numel() for p in ckpt.parameters())
                except Exception as e:
                    entry["load_error"] = str(e)
                    
            models_data[crop_name][arch_name] = entry
            print(f"[{crop_name.upper()} - {arch_name}] Params: {entry['param_count']:,} | PTH: {entry['pth_size_bytes'] / 1e6:.2f} MB | ONNX: {entry['onnx_exists']}")

    return models_data


def audit_routes():
    print("\n=== AUDITING BACKEND API ROUTES ===")
    from app.main import app
    from app.api.routes import api_router
    from fastapi.routing import APIRoute
    routes = []
    
    # 1. Top-level routes
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path not in ["/openapi.json", "/docs", "/redoc"]:
            routes.append({
                "path": route.path,
                "name": route.name,
                "methods": sorted(list(route.methods)),
                "tags": list(route.tags) if route.tags else [],
                "summary": route.summary or "",
            })
            
    # 2. Included API Router routes under /api/v1
    for route in api_router.routes:
        if isinstance(route, APIRoute):
            full_path = f"/api/v1{route.path}"
            routes.append({
                "path": full_path,
                "name": route.name,
                "methods": sorted(list(route.methods)),
                "tags": list(route.tags) if route.tags else [],
                "summary": route.summary or "",
            })
            
    print(f"Total verified FastAPI APIRoutes: {len(routes)}")
    for r in routes:
        print(f"  {','.join(r['methods']):<10} {r['path']:<45} [{','.join(r['tags'])}]")
    return routes


def audit_db_models():
    print("\n=== AUDITING DATABASE MODELS ===")
    from app.models import user, farm, crop_cycle, diagnosis, disease
    from app.db.base import Base
    tables = [table.name for table in Base.metadata.sorted_tables]
    print(f"Total database tables in metadata: {tables}")
    return tables


def audit_datasets():
    print("\n=== AUDITING DATASET MANIFESTS & STORAGE ===")
    datasets_info = {}
    proc_dir = PROJECT_ROOT / "datasets" / "processed"
    if proc_dir.exists():
        for crop_dir in proc_dir.iterdir():
            if crop_dir.is_dir():
                manifests = list(crop_dir.glob("*.csv")) + list(crop_dir.glob("*/*.csv"))
                total_files = sum(1 for _ in crop_dir.rglob("*.jpg")) + sum(1 for _ in crop_dir.rglob("*.jpeg")) + sum(1 for _ in crop_dir.rglob("*.png"))
                datasets_info[crop_dir.name] = {
                    "manifests": [str(m.relative_to(PROJECT_ROOT)) for m in manifests],
                    "image_file_count": total_files,
                }
                print(f"Crop: {crop_dir.name} | Image files: {total_files} | Manifests: {len(manifests)}")
    return datasets_info


def main():
    models_data = audit_models()
    routes_data = audit_routes()
    db_tables = audit_db_models()
    datasets_data = audit_datasets()

    output = {
        "models": models_data,
        "routes": routes_data,
        "database_tables": db_tables,
        "datasets": datasets_data,
    }

    out_file = PROJECT_ROOT / "scripts" / "audit_evidence_dump.json"
    with open(out_file, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n[SUCCESS] Audit evidence saved to {out_file}")

if __name__ == "__main__":
    main()
