import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.core.security import get_password_hash, create_access_token
from app.models.user import User, UserRole
from app.models.farm import Farm
from app.models.crop_cycle import CropCycle

# In-memory SQLite engine for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    # Create all tables in the test database
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db: Session) -> User:
    user = User(
        name="Ramesh Patil",
        email="ramesh@example.com",
        password_hash=get_password_hash("password123"),
        preferred_language="mr",
        role=UserRole.FARMER,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_token(test_user: User) -> str:
    return create_access_token(subject=test_user.id)


@pytest.fixture(scope="function")
def auth_headers(auth_token: str) -> dict:
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="function")
def other_user(db: Session) -> User:
    user = User(
        name="Suresh Shinde",
        email="suresh@example.com",
        password_hash=get_password_hash("securepwd456"),
        preferred_language="en",
        role=UserRole.FARMER,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def other_token(other_user: User) -> str:
    return create_access_token(subject=other_user.id)


@pytest.fixture(scope="function")
def other_auth_headers(other_token: str) -> dict:
    return {"Authorization": f"Bearer {other_token}"}


@pytest.fixture(scope="function")
def test_farm(db: Session, test_user: User) -> Farm:
    farm = Farm(
        user_id=test_user.id,
        name="Green Valley Farm",
        area=5.5,
        soil_type="Black Cotton",
        irrigation="Drip",
        latitude=19.7515,
        longitude=75.7139,
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


@pytest.fixture(scope="function")
def test_crop(db: Session, test_farm: Farm) -> CropCycle:
    crop = CropCycle(
        farm_id=test_farm.id,
        crop="Cotton",
        variety="Bt Cotton 659",
        growth_stage="Vegetative",
        status="active",
    )
    db.add(crop)
    db.commit()
    db.refresh(crop)
    return crop
