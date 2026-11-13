"""
PikVaidya AI — Administrative Management & System Telemetry API
==============================================================
Provides platform governance, telemetry metrics, user management,
and access to immutable administrative audit trails. Restricted to ADMIN role.
"""

import sys
import os
import psutil
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.farm import Farm
from app.models.crop_cycle import CropCycle
from app.models.diagnosis import Diagnosis
from app.models.expert_review import ExpertReview
from app.models.audit_log import AuditLog
from app.services.model_service import model_service

router = APIRouter()


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int]
    action: str
    target_type: str
    target_id: Optional[str]
    details: Optional[str]
    ip_address: Optional[str]
    created_at: datetime


class UserAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool
    preferred_language: str
    created_at: datetime


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Enforces strict role-based access control for administrative endpoints."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    return current_user


@router.get("/telemetry", summary="Platform telemetry and runtime health")
def get_system_telemetry(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Returns runtime system vitals: memory, CPU, loaded models, and process uptime."""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()

    return {
        "status": "OPERATIONAL",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "python_version": sys.version.split()[0],
            "pid": os.getpid(),
            "cpu_percent": process.cpu_percent(interval=None),
            "memory_rss_mb": round(mem_info.rss / (1024 * 1024), 2),
            "memory_vms_mb": round(mem_info.vms / (1024 * 1024), 2),
        },
        "model_service": {
            "loaded": getattr(model_service, "is_loaded", False),
            "version": getattr(model_service, "model_version", "1.0.0"),
            "architecture": getattr(model_service, "architecture", "MobileNetV3-Large"),
            "target_layer": getattr(model_service, "target_layer_name", "features[16]"),
        },
        "database": {
            "users_count": db.query(User).count(),
            "farms_count": db.query(Farm).count(),
            "crops_count": db.query(CropCycle).count(),
            "diagnoses_count": db.query(Diagnosis).count(),
            "expert_reviews_count": db.query(ExpertReview).count(),
        }
    }


@router.get("/summary", summary="System business summary counts")
def get_system_summary(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Returns executive overview metrics on platform adoption and diagnosis statistics."""
    return {
        "farmers": db.query(User).filter(User.role == UserRole.FARMER).count(),
        "experts": db.query(User).filter(User.role == UserRole.EXPERT).count(),
        "admins": db.query(User).filter(User.role == UserRole.ADMIN).count(),
        "farms": db.query(Farm).count(),
        "crop_cycles": db.query(CropCycle).count(),
        "diagnoses_total": db.query(Diagnosis).count(),
        "expert_reviews_pending": db.query(ExpertReview).filter(ExpertReview.status == "PENDING").count(),
        "expert_reviews_completed": db.query(ExpertReview).filter(ExpertReview.status.in_(["CONFIRMED", "CORRECTED"])).count(),
    }


@router.get("/audit-logs", response_model=List[AuditLogResponse], summary="List security and admin audit logs")
def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None, description="Filter by action name"),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Retrieves immutable audit trail of system activities."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    logs = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()
    return logs


@router.get("/users", response_model=List[UserAdminResponse], summary="List all platform users")
def list_users(
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Lists registered accounts with optional role-based filtering."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    users = query.order_by(desc(User.created_at)).offset(offset).limit(limit).all()
    return users
