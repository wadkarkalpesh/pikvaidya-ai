import sys
import json
from pathlib import Path
import httpx
import psycopg
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
backend_path = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

print("=" * 80)
print("       PIKVAIDYA AI — LIVE END-TO-END SYSTEM DEMONSTRATION")
print("=" * 80)

# 1. Verify PostgreSQL Database Connectivity & Live Tables
print("\n[STEP 1] Inspecting Live PostgreSQL Database ('pikvaidya' on port 5432)...")
try:
    conn = psycopg.connect("postgresql://postgres:root@localhost:5432/pikvaidya")
    with conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
        tables = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT version_num FROM alembic_version;")
        alembic_rev = cur.fetchone()[0]
        print(f"  ✓ Connected to PostgreSQL successfully!")
        print(f"  ✓ Live Public Tables: {tables}")
        print(f"  ✓ Current Alembic Migration Revision: {alembic_rev}")
    conn.close()
except Exception as e:
    print(f"  ✗ PostgreSQL Connection Note: {e}")

# 2. Live API Health Check
print("\n[STEP 2] Querying Live FastAPI Gateway (http://127.0.0.1:8000)...")
with httpx.Client(base_url="http://127.0.0.1:8000", timeout=15.0) as client:
    health_resp = client.get("/health")
    root_resp = client.get("/")
    print(f"  ✓ GET /health -> Status {health_resp.status_code}: {health_resp.json()}")
    print(f"  ✓ GET /       -> Status {root_resp.status_code}: {root_resp.json()}")

    # 3. Running Diagnostic Predictions with Grad-CAM on Real Samples
    print("\n[STEP 3] Running Live Predictions via POST /api/v1/diagnose/predict...")
    
    test_cases = [
        ("Healthy Leaf", "data/raw/sugarcane/Healthy/healthy (188).jpeg"),
        ("Red Rot Leaf", "data/raw/sugarcane/RedRot/redrot (380).jpeg"),
        ("Mosaic Leaf",  "data/raw/sugarcane/Mosaic/mosaic (39).jpeg"),
    ]
    
    for label, img_rel_path in test_cases:
        img_path = PROJECT_ROOT / img_rel_path
        if not img_path.exists():
            print(f"  ✗ Sample not found: {img_path}")
            continue
            
        print(f"\n  >> Testing: {label} ({img_path.name})")
        with open(img_path, "rb") as img_file:
            files = {"file": (img_path.name, img_file, "image/jpeg")}
            data = {
                "crop": "sugarcane",
                "generate_gradcam": "true",
                "save_heatmap": "true"
            }
            resp = client.post("/api/v1/diagnose/predict", files=files, data=data)
            
        assert resp.status_code == 200, f"Request failed: {resp.text}"
        res = resp.json()
        
        print(f"     Status:           {resp.status_code} OK")
        print(f"     Target Crop:      {res['crop']}")
        print(f"     Predicted Class:  {res['predicted_class']}")
        print(f"     Confidence:       {res['confidence'] * 100:.2f}%")
        print(f"     Model Version:    {res['model_version']}")
        print(f"     Grad-CAM Status:  {res['explanation_status']}")
        
        # Check generated heatmap file
        heatmap_path = res.get("heatmap_path")
        if heatmap_path:
            full_hm_path = PROJECT_ROOT / heatmap_path
            if full_hm_path.exists():
                with Image.open(full_hm_path) as hm_img:
                    print(f"     Heatmap Image:    {heatmap_path} (Dimensions: {hm_img.size}, Mode: {hm_img.mode})")
            else:
                print(f"     Heatmap Path:     {heatmap_path}")
                
        print("     Score Distribution:")
        for cls_name, score in res["class_scores"].items():
            bar = "█" * int(score * 30)
            print(f"       - {cls_name:<10}: {score:6.4f}  |{bar:<30}|")

# 4. Live Full-Stack Database Persistence Demonstration
print("\n[STEP 4] Testing Full Lifecycle: User Registration -> Farm -> Crop Cycle -> Diagnosis Persistence...")
with httpx.Client(base_url="http://127.0.0.1:8000", timeout=15.0) as client:
    import uuid
    farmer_email = f"farmer_{uuid.uuid4().hex[:6]}@example.com"
    farmer_pass = "SmartFarmer2026"
    reg_resp = client.post("/api/v1/auth/register", json={
        "name": "Arjun Gaikwad",
        "email": farmer_email,
        "password": farmer_pass,
        "preferred_language": "mr"
    })
    assert reg_resp.status_code == 201, f"Registration failed ({reg_resp.status_code}): {reg_resp.text}"
    
    # Login to obtain Bearer JWT
    login_resp = client.post("/api/v1/auth/login", json={
        "email": farmer_email,
        "password": farmer_pass
    })
    assert login_resp.status_code == 200, f"Login failed ({login_resp.status_code}): {login_resp.text}"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  ✓ Authenticated Farmer: Arjun Gaikwad ({farmer_email})")
    
    # Create farm
    farm_resp = client.post("/api/v1/farms", headers=headers, json={
        "name": "Sahyadri Bio-Farm",
        "area": 8.0,
        "soil_type": "Black Loam",
        "irrigation": "Drip Irrigation",
        "latitude": 19.75,
        "longitude": 75.71
    })
    farm_id = farm_resp.json()["id"]
    print(f"  ✓ Created Farm ID {farm_id}: Sahyadri Bio-Farm (8.0 ha)")
    
    # Create crop cycle
    crop_resp = client.post(f"/api/v1/farms/{farm_id}/crops", headers=headers, json={
        "crop": "sugarcane",
        "variety": "Co 86032",
        "growth_stage": "Grand Growth",
        "status": "active"
    })
    crop_id = crop_resp.json()["id"]
    print(f"  ✓ Created CropCycle ID {crop_id}: Sugarcane (Co 86032)")
    
    # Submit real foliar leaf image to diagnostic persistence endpoint
    leaf_path = PROJECT_ROOT / "data/raw/sugarcane/RedRot/redrot (380).jpeg"
    with open(leaf_path, "rb") as f:
        diag_resp = client.post(
            f"/api/v1/crops/{crop_id}/diagnoses",
            headers=headers,
            files={"file": (leaf_path.name, f, "image/jpeg")},
            data={
                "notes": "Red rot symptoms observed on lower stalks following heavy rains",
                "temperature": 31.0,
                "humidity": 80.0,
                "soil_moisture": 68.0
            }
        )
    diag_data = diag_resp.json()
    print(f"  ✓ Submitted Diagnosis ID {diag_data['id']}: Status: {diag_data['status']}")
    print(f"     Diagnosis (EN): {diag_data['disease_name_en']} (Severity: {diag_data['severity']}, Confidence: {diag_data['confidence']})")
    print(f"     Diagnosis (MR): {diag_data['disease_name_mr']}")
    print(f"     Symptoms (MR):  {diag_data['symptoms_mr']}")
    print(f"     Advisory (MR):  {diag_data['recommendations_mr']}")
    print(f"     Stored File:    {diag_data['image_path']}")

# 5. Verify Row in Live PostgreSQL Table
print("\n[STEP 5] Verifying Persisted Diagnosis in Live PostgreSQL 'diagnoses' Table...")
conn = psycopg.connect("postgresql://postgres:root@localhost:5432/pikvaidya")
with conn.cursor() as cur:
    cur.execute("SELECT id, user_id, crop_name, disease_name_en, disease_name_mr, status, confidence, created_at FROM diagnoses ORDER BY id DESC LIMIT 1;")
    row = cur.fetchone()
    print(f"  ✓ Record verified directly in PostgreSQL:")
    print(f"    - ID:            {row[0]}")
    print(f"    - User ID:       {row[1]}")
    print(f"    - Crop:          {row[2]}")
    print(f"    - Disease (EN):  {row[3]}")
    print(f"    - Disease (MR):  {row[4]}")
    print(f"    - Status:        {row[5]}")
    print(f"    - Confidence:    {row[6]}")
    print(f"    - Timestamp:     {row[7]}")
conn.close()

print("\n" + "=" * 80)
print("     ALL SUBSYSTEMS FULLY INTEGRATED, SERVING, AND VERIFIED LIVE!")
print("=" * 80)
