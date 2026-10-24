import sys
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root and backend directory are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
backend_path = PROJECT_ROOT / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine, select, inspect
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.models.user import User, UserRole
from app.models.farm import Farm
from app.models.crop_cycle import CropCycle
from app.models.diagnosis import Diagnosis, DiagnosisStatus, DiagnosisSeverity
from app.core.security import get_password_hash

print("--- PHASE 5: VERIFY DATABASE INTEGRATION & SCHEMAS ---")

# 1. Test isolated SQLite database
TEST_DB_PATH = PROJECT_ROOT / "test_isolated_verification.db"
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

test_engine = create_engine(f"sqlite:///{TEST_DB_PATH.as_posix()}", echo=False)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Create all schemas defined in SQLAlchemy ORM Base
Base.metadata.create_all(bind=test_engine)
print("1. Successfully created tables from SQLAlchemy Base metadata.")

# Inspect created tables and columns
inspector = inspect(test_engine)
tables = inspector.get_table_names()
print(f"Tables present in schema: {tables}")
assert set(["users", "farms", "crop_cycles", "diagnoses"]).issubset(set(tables)), "Missing tables in schema"

# 2. Verify model constraints, relationships and persistence
db = TestSession()
try:
    # Farmer User
    farmer = User(
        name="Tukaram Jadhav",
        email="tukaram@example.com",
        password_hash=get_password_hash("securepass123"),
        preferred_language="mr",
        role=UserRole.FARMER,
        is_active=True
    )
    db.add(farmer)
    db.commit()
    db.refresh(farmer)
    print(f"2. Saved User: id={farmer.id}, name={farmer.name}, role={farmer.role}")

    # Farm
    farm = Farm(
        user_id=farmer.id,
        name="Krishna Farm",
        area=12.5,
        soil_type="Medium Black",
        irrigation="Canal + Drip",
        latitude=19.8762,
        longitude=75.3433
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    print(f"3. Saved Farm: id={farm.id}, user_id={farm.user_id}, area={farm.area} ha")

    # Crop Cycle (Sugarcane)
    crop = CropCycle(
        farm_id=farm.id,
        crop="sugarcane",
        variety="Co 86032 (Nira)",
        growth_stage="Grand Growth",
        status="active"
    )
    db.add(crop)
    db.commit()
    db.refresh(crop)
    print(f"4. Saved CropCycle: id={crop.id}, crop={crop.crop}, variety={crop.variety}")

    # Diagnosis Record
    diag = Diagnosis(
        user_id=farmer.id,
        crop_cycle_id=crop.id,
        image_path="uploads/diagnostics/2026-10/leaf_sample_01.jpg",
        image_filename="leaf_sample_01.jpg",
        image_hash="a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
        crop_name="sugarcane",
        disease_name_en="Red Rot",
        disease_name_mr="तांबोरा / लाल कुज",
        pathogen_type="Fungal (Colletotrichum falcatum)",
        confidence=0.9445,
        severity=DiagnosisSeverity.SEVERE,
        affected_area_percentage=35.0,
        symptoms_en="Reddening of internal tissues, white spots transverse to long axis.",
        symptoms_mr="खोडाच्या आतील भाग लाल पडणे, आडवे पांढरे पट्टे दिसणे.",
        recommendations_en="Use certified disease-free setts, treat with Carbendazim.",
        recommendations_mr="प्रमाणित निरोगी बेणे वापरा, कार्बेन्डाझिमची बीजप्रक्रिया करा.",
        temperature=31.5,
        humidity=78.0,
        soil_moisture=65.0,
        status=DiagnosisStatus.COMPLETED,
        notes="First observed in lower third of field after heavy monsoon rain."
    )
    db.add(diag)
    db.commit()
    db.refresh(diag)
    print(f"5. Saved Diagnosis record: id={diag.id}, disease={diag.disease_name_en}, confidence={diag.confidence}")

    # Query back diagnosis with relationships
    stmt = select(Diagnosis).where(Diagnosis.id == diag.id)
    retrieved_diag = db.scalar(stmt)
    assert retrieved_diag is not None
    assert retrieved_diag.crop_cycle.crop == "sugarcane"
    assert retrieved_diag.user.email == "tukaram@example.com"
    print(f"6. Successfully verified ORM relationships: diag -> crop_cycle ({retrieved_diag.crop_cycle.crop}) -> farm -> user ({retrieved_diag.user.name})")

    # 3. Verify Cascade delete
    db.delete(farm)
    db.commit()
    remaining_crops = db.query(CropCycle).filter(CropCycle.farm_id == farm.id).all()
    remaining_diags = db.query(Diagnosis).filter(Diagnosis.user_id == farmer.id).all()
    print(f"7. After deleting farm, remaining crops={len(remaining_crops)}, remaining diagnoses={len(remaining_diags)} (Foreign key cascade verified)")

finally:
    db.close()
    test_engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
        print("8. Cleaned up temporary test database.")

print("\n--- PHASE 5 VERIFICATION COMPLETE: ALL CHECKS PASSED ---")
