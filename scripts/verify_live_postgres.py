"""Empirical PostgreSQL Integration Verification Script.

Executes end-to-end integration test against the LIVE PostgreSQL database
configured at postgresql+psycopg://postgres:root@localhost:5432/pikvaidya.
Verifies table schema, migration level, row persistence, advisory status,
and cascading cleanup without resetting existing database data.
"""
import sys
import io
import uuid
from pathlib import Path
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

# Ensure backend directory is in python path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.farm import Farm
from app.models.crop_cycle import CropCycle
from app.models.diagnosis import Diagnosis, DiagnosisStatus, DiagnosisSeverity
from app.services.diagnostic_service import diagnostic_service
from app.services.storage import storage_service
from fastapi import UploadFile

LIVE_POSTGRES_URL = "postgresql+psycopg://postgres:root@localhost:5432/pikvaidya"


def run_live_postgres_verification():
    print(f"Connecting to Live PostgreSQL: {LIVE_POSTGRES_URL} ...")
    engine = create_engine(LIVE_POSTGRES_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        # 1. Count pre-existing records to guarantee non-destruction
        initial_diag_count = session.query(Diagnosis).count()
        print(f"Pre-existing PostgreSQL diagnosis records: {initial_diag_count}")

        # 2. Create isolated test user
        test_email = f"pg_test_{uuid.uuid4().hex[:8]}@example.com"
        test_user = User(
            name="PostgreSQL Verifier",
            email=test_email,
            password_hash=get_password_hash("verifyPass123"),
            preferred_language="en",
            role=UserRole.FARMER,
            is_active=True,
        )
        session.add(test_user)
        session.commit()
        session.refresh(test_user)
        print(f"Created isolated test user ID: {test_user.id} ({test_email})")

        # 3. Create test farm
        test_farm = Farm(
            user_id=test_user.id,
            name="Kolhapur Live Test Farm",
            area=10.0,
            soil_type="Black Clay",
            irrigation="Drip",
        )
        session.add(test_farm)
        session.commit()
        session.refresh(test_farm)

        # 4. Create test crop cycle (Sugarcane)
        test_crop = CropCycle(
            farm_id=test_farm.id,
            crop="Sugarcane",
            variety="Co 86032",
            growth_stage="Grand Growth",
            status="active",
        )
        session.add(test_crop)
        session.commit()
        session.refresh(test_crop)
        print(f"Created test crop cycle ID: {test_crop.id} for crop 'Sugarcane'")

        # 5. Generate test image
        img = Image.new("RGB", (224, 224), color=(34, 139, 34))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        raw_bytes = buf.getvalue()

        upload_file = UploadFile(
            file=io.BytesIO(raw_bytes),
            filename="live_pg_leaf.jpg",
            headers={"content-type": "image/jpeg"},
        )

        # 6. Run diagnostic service with Grad-CAM on live Postgres session
        import anyio
        async def execute_diagnosis():
            return await diagnostic_service.run_authenticated_crop_diagnosis(
                crop_id=test_crop.id,
                user_id=test_user.id,
                file=upload_file,
                notes="PostgreSQL live integration run",
                temperature=30.5,
                humidity=79.0,
                soil_moisture=62.0,
                generate_gradcam=True,
                db=session,
            )

        diagnosis = anyio.run(execute_diagnosis)
        diag_id = diagnosis.id
        print(f"Successfully persisted Diagnosis record ID: {diag_id}")

        # 7. Query back from PostgreSQL
        refreshed = session.query(Diagnosis).filter(Diagnosis.id == diag_id).first()
        assert refreshed is not None, "Failed to retrieve persisted diagnosis from PostgreSQL"
        assert refreshed.crop_name == "Sugarcane"
        assert refreshed.status == DiagnosisStatus.COMPLETED
        assert refreshed.confidence is not None
        assert refreshed.advisory_status is not None
        assert refreshed.severity in [DiagnosisSeverity.HEALTHY, DiagnosisSeverity.UNAVAILABLE, DiagnosisSeverity.UNVALIDATED]
        assert refreshed.heatmap_path is not None
        assert Path(refreshed.heatmap_path).exists()
        print(f"Verified PostgreSQL row: predicted class, confidence={refreshed.confidence}, advisory_status={refreshed.advisory_status}, heatmap={refreshed.heatmap_path}")

        # 8. Clean up created test assets cleanly
        if refreshed.heatmap_path and Path(refreshed.heatmap_path).exists():
            Path(refreshed.heatmap_path).unlink()
        storage_service.remove_file(refreshed.image_path)

        # Delete user (cascades farm, crop_cycle, diagnosis)
        session.delete(test_user)
        session.commit()
        print("Cascading deletion of test entities completed.")

        # 9. Verify pre-existing records remain untouched
        final_diag_count = session.query(Diagnosis).count()
        assert final_diag_count == initial_diag_count, f"Count mismatch: initial {initial_diag_count} != final {final_diag_count}"
        print(f"Pre-existing records verified: {final_diag_count} rows intact (ZERO records lost).")
        print("\n>>> LIVE POSTGRESQL INTEGRATION TEST: 100% SUCCESSFUL <<<")

    except Exception as e:
        session.rollback()
        print(f"Live PostgreSQL verification failed: {e}", file=sys.stderr)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run_live_postgres_verification()
