from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.models.farm import Farm
from app.schemas.farm import FarmCreate, FarmUpdate, FarmResponse

router = APIRouter()


@router.post("", response_model=FarmResponse, status_code=status.HTTP_201_CREATED)
def create_farm(
    farm_in: FarmCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new farm for the authenticated user."""
    farm = Farm(
        user_id=current_user.id,
        name=farm_in.name,
        area=farm_in.area,
        soil_type=farm_in.soil_type,
        irrigation=farm_in.irrigation,
        latitude=farm_in.latitude,
        longitude=farm_in.longitude,
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


@router.get("", response_model=List[FarmResponse])
def list_farms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all farms owned by the authenticated user."""
    farms = db.query(Farm).filter(Farm.user_id == current_user.id).all()
    return farms


@router.get("/{farm_id}", response_model=FarmResponse)
def get_farm(
    farm_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific farm by ID."""
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found."
        )
    if farm.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this farm."
        )
    return farm


@router.put("/{farm_id}", response_model=FarmResponse)
def update_farm(
    farm_id: int,
    farm_in: FarmUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a farm owned by the authenticated user."""
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found."
        )
    if farm.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this farm."
        )

    update_data = farm_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(farm, field, value)

    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


@router.delete("/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farm(
    farm_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a farm owned by the authenticated user."""
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found."
        )
    if farm.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this farm."
        )

    db.delete(farm)
    db.commit()
    return None
