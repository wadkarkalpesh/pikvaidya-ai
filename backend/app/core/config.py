import logging
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

INSECURE_DEFAULT_SECRET_KEY = "supersecretpikvaidyadefaultkeychangeinproduction1234567890"


class Settings(BaseSettings):
    PROJECT_NAME: str = "PikVaidya AI"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # Security
    SECRET_KEY: str = INSECURE_DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Database
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/pikvaidya"
    
    # Storage & Uploads
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".webp"]

    # Machine Learning Model Serving
    MODEL_CHECKPOINT_PATH: str = "models/sugarcane/efficientnet_b0/best_model.pth"
    MODEL_ARCH_NAME: str = "EfficientNet-B0"
    MODEL_VERSION: str = "EfficientNet-B0-v1.0"

    # Diagnostic Safety & Confidence Thresholds (Provisional, requires field calibration)
    CONFIDENCE_THRESHOLD_HIGH: float = 0.75
    CONFIDENCE_THRESHOLD_MODERATE: float = 0.50

    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        # Check environment from data if available
        env = info.data.get("ENVIRONMENT", "development").lower() if info.data else "development"
        if env == "production":
            if not v or v == INSECURE_DEFAULT_SECRET_KEY or len(v) < 32:
                raise ValueError(
                    "Production security violation: A secure, non-default SECRET_KEY of at least 32 characters must be configured in environment."
                )
        return v

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors(cls, v: List[str], info) -> List[str]:
        env = info.data.get("ENVIRONMENT", "development").lower() if info.data else "development"
        if env == "production" and "*" in v:
            raise ValueError(
                "Production security violation: Wildcard CORS ('*') is forbidden in production environment."
            )
        return v

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

