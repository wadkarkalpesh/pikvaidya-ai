"""
PikVaidya AI — Notification & Weather Alert Delivery API
========================================================
Manages farmer alert feeds, agrometeorological warnings,
diagnosis review notifications, and monitoring reminders.
"""

from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.notification import Notification, NotificationType, NotificationSeverity

router = APIRouter()


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    message: str
    notification_type: NotificationType
    severity: NotificationSeverity
    is_read: bool
    related_diagnosis_id: Optional[int] = None
    created_at: datetime


class CreateNotificationRequest(BaseModel):
    user_id: int
    title: str
    message: str
    notification_type: NotificationType = NotificationType.SYSTEM
    severity: NotificationSeverity = NotificationSeverity.INFO
    related_diagnosis_id: Optional[int] = None


@router.get("", response_model=List[NotificationResponse], summary="List user notifications")
def list_notifications(
    unread_only: bool = Query(False, description="Filter for unread notifications only"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves chronological notification feed for the authenticated farmer or expert."""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    
    notifications = query.order_by(desc(Notification.created_at)).offset(offset).limit(limit).all()
    return notifications


@router.get("/unread-count", summary="Get unread notifications count")
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns number of unread notifications for badge rendering."""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False)
    ).count()
    return {"unread_count": count}


@router.post("/{notification_id}/read", response_model=NotificationResponse, summary="Mark notification as read")
def mark_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marks an unread notification as acknowledged."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/create", response_model=NotificationResponse, summary="Dispatch new alert (Admin/System)")
def create_notification(
    payload: CreateNotificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dispatches a notification to a specific user (restricted to system or admin roles)."""
    if current_user.role.value not in ("ADMIN", "EXPERT") and current_user.id != payload.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to dispatch notifications to third-party accounts"
        )

    notification = Notification(
        user_id=payload.user_id,
        title=payload.title,
        message=payload.message,
        notification_type=payload.notification_type,
        severity=payload.severity,
        related_diagnosis_id=payload.related_diagnosis_id,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification
