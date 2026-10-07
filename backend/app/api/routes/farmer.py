from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.user import FarmerProfileUpdate, UserResponse

router = APIRouter()


@router.get("/profile", response_model=UserResponse)
def get_farmer_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Retrieve the profile of the currently authenticated farmer."""
    return current_user


@router.put("/profile", response_model=UserResponse)
def update_farmer_profile(
    profile_in: FarmerProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update profile details for the currently authenticated farmer."""
    if profile_in.name is not None:
        current_user.name = profile_in.name
    if profile_in.preferred_language is not None:
        current_user.preferred_language = profile_in.preferred_language

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user
