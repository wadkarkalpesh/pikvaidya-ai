"""
PikVaidya AI — Human Expert Review & Diagnosis Verification Workflow
====================================================================
Enables certified agricultural experts and KVK agronomists to review,
confirm, or correct AI diagnoses, maintaining an immutable audit trail
without mutating the baseline training datasets.
"""

from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.diagnosis import Diagnosis
from app.models.expert_review import ExpertReview, ReviewStatus
from app.models.audit_log import AuditLog
from app.models.notification import Notification, NotificationType, NotificationSeverity

router = APIRouter()


class RequestReviewRequest(BaseModel):
    diagnosis_id: int
    farmer_notes: Optional[str] = None


class SubmitReviewEvaluation(BaseModel):
    is_agreement: bool
    corrected_disease_en: Optional[str] = None
    corrected_disease_mr: Optional[str] = None
    pathogen_type: Optional[str] = None
    expert_notes: Optional[str] = None
    recommended_treatment: Optional[str] = None


class ExpertReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    diagnosis_id: int
    farmer_id: int
    expert_id: Optional[int] = None
    status: ReviewStatus
    original_disease_en: str
    original_confidence: Optional[float] = None
    farmer_notes: Optional[str] = None
    is_agreement: Optional[bool] = None
    corrected_disease_en: Optional[str] = None
    corrected_disease_mr: Optional[str] = None
    pathogen_type: Optional[str] = None
    expert_notes: Optional[str] = None
    recommended_treatment: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None


@router.post("/request-review", response_model=ExpertReviewResponse, summary="Farmer requests human expert review")
def request_expert_review(
    payload: RequestReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submits an uncertain or contested AI diagnosis to the agricultural expert queue."""
    diagnosis = db.query(Diagnosis).filter(Diagnosis.id == payload.diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnosis not found")

    # Authorize: Farmer must own the diagnosis or be an Admin
    if diagnosis.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to third-party diagnosis")

    # Check if a review is already requested
    existing = db.query(ExpertReview).filter(ExpertReview.diagnosis_id == diagnosis.id).first()
    if existing:
        return existing

    review = ExpertReview(
        diagnosis_id=diagnosis.id,
        farmer_id=diagnosis.user_id,
        status=ReviewStatus.PENDING,
        original_disease_en=diagnosis.disease_name_en or "Unknown",
        original_confidence=diagnosis.confidence,
        farmer_notes=payload.farmer_notes,
    )
    db.add(review)

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="EXPERT_REVIEW_REQUESTED",
        target_type="DIAGNOSIS",
        target_id=str(diagnosis.id),
        details=f"Farmer {current_user.name} requested expert review for {diagnosis.disease_name_en}."
    )
    db.add(audit)
    db.commit()
    db.refresh(review)
    return review


@router.get("/pending-reviews", response_model=List[ExpertReviewResponse], summary="List pending reviews (Experts/Admins)")
def list_pending_reviews(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetches queue of pending diagnoses requiring agronomist review. Restricted to EXPERT and ADMIN roles."""
    if current_user.role not in (UserRole.EXPERT, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to certified agricultural experts and administrators"
        )

    reviews = db.query(ExpertReview).filter(
        ExpertReview.status.in_([ReviewStatus.PENDING, ReviewStatus.UNDER_REVIEW])
    ).order_by(desc(ExpertReview.created_at)).offset(offset).limit(limit).all()
    return reviews


@router.post("/reviews/{review_id}/submit", response_model=ExpertReviewResponse, summary="Submit expert review evaluation")
def submit_expert_evaluation(
    review_id: int,
    payload: SubmitReviewEvaluation,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submits expert judgment on an AI diagnosis. Logs the correction without mutating training data."""
    if current_user.role not in (UserRole.EXPERT, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to certified agricultural experts and administrators"
        )

    review = db.query(ExpertReview).filter(ExpertReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expert review record not found")

    review.expert_id = current_user.id
    review.is_agreement = payload.is_agreement
    review.status = ReviewStatus.CONFIRMED if payload.is_agreement else ReviewStatus.CORRECTED
    review.corrected_disease_en = payload.corrected_disease_en
    review.corrected_disease_mr = payload.corrected_disease_mr
    review.pathogen_type = payload.pathogen_type
    review.expert_notes = payload.expert_notes
    review.recommended_treatment = payload.recommended_treatment
    review.reviewed_at = datetime.now(timezone.utc)

    # Dispatch notification to the farmer
    msg = (
        f"An agricultural expert has completed the review of your diagnosis. Result: "
        f"{'Diagnosis Confirmed' if payload.is_agreement else 'Diagnosis Corrected to ' + (payload.corrected_disease_en or '')}. "
        f"Notes: {payload.expert_notes or 'None'}"
    )
    notification = Notification(
        user_id=review.farmer_id,
        title="Expert Diagnosis Review Complete",
        message=msg,
        notification_type=NotificationType.EXPERT_REVIEW,
        severity=NotificationSeverity.INFO,
        related_diagnosis_id=review.diagnosis_id
    )
    db.add(notification)

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="EXPERT_EVALUATION_SUBMITTED",
        target_type="EXPERT_REVIEW",
        target_id=str(review.id),
        details=f"Expert {current_user.name} evaluated review {review.id}: agreement={payload.is_agreement}."
    )
    db.add(audit)
    db.commit()
    db.refresh(review)
    return review
