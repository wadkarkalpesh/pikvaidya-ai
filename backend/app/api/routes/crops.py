from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.models.farm import Farm
from app.models.crop_cycle import CropCycle
from app.schemas.crop_cycle import CropCycleCreate, CropCycleUpdate, CropCycleResponse

router = APIRouter()


def _get_user_farm(farm_id: int, user_id: int, db: Session) -> Farm:
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found."
        )
    if farm.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access crops in this farm."
        )
    return farm


def _get_user_crop(crop_id: int, user_id: int, db: Session) -> CropCycle:
    crop = (
        db.query(CropCycle)
        .join(Farm, CropCycle.farm_id == Farm.id)
        .filter(CropCycle.id == crop_id)
        .first()
    )
    if not crop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crop cycle not found."
        )
    if crop.farm.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this crop cycle."
        )
    return crop


# Farm-nested crop endpoints
@router.post("/farms/{farm_id}/crops", response_model=CropCycleResponse, status_code=status.HTTP_201_CREATED)
def create_crop_cycle(
    farm_id: int,
    crop_in: CropCycleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new crop cycle under a specific farm."""
    _get_user_farm(farm_id, current_user.id, db)

    crop = CropCycle(
        farm_id=farm_id,
        crop=crop_in.crop,
        variety=crop_in.variety,
        sowing_date=crop_in.sowing_date,
        growth_stage=crop_in.growth_stage,
        status=crop_in.status,
    )
    db.add(crop)
    db.commit()
    db.refresh(crop)
    return crop


@router.get("/farms/{farm_id}/crops", response_model=List[CropCycleResponse])
def list_crop_cycles_for_farm(
    farm_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all crop cycles in a specific farm owned by the user."""
    _get_user_farm(farm_id, current_user.id, db)
    return db.query(CropCycle).filter(CropCycle.farm_id == farm_id).all()


# Direct crop endpoints
@router.get("/crops/{crop_id}", response_model=CropCycleResponse)
def get_crop_cycle(
    crop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieve details of a crop cycle."""
    return _get_user_crop(crop_id, current_user.id, db)


@router.put("/crops/{crop_id}", response_model=CropCycleResponse)
def update_crop_cycle(
    crop_id: int,
    crop_in: CropCycleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a crop cycle."""
    crop = _get_user_crop(crop_id, current_user.id, db)

    update_data = crop_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(crop, field, value)

    db.add(crop)
    db.commit()
    db.refresh(crop)
    return crop


@router.delete("/crops/{crop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_crop_cycle(
    crop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a crop cycle."""
    crop = _get_user_crop(crop_id, current_user.id, db)
    db.delete(crop)
    db.commit()
    return None
