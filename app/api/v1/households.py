from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.household import Household, HouseholdUser
from app.schemas.household import (
    HouseholdCreate,
    Household as HouseholdSchema,
    HouseholdJoinRequest
)
from app.api.deps import get_current_user

router = APIRouter()


@router.post("/", response_model=HouseholdSchema)
def create_household(
    household_in: HouseholdCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new household."""
    # Create household
    db_household = Household(name=household_in.name)
    db.add(db_household)
    db.commit()
    db.refresh(db_household)

    # Add creator as household member
    household_user = HouseholdUser(
        household_id=db_household.id,
        user_id=current_user.id,
        share_default=1.0
    )
    db.add(household_user)
    db.commit()

    return db_household


@router.get("/{household_id}", response_model=HouseholdSchema)
def get_household(
    household_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get household details."""
    household = db.query(Household).filter(Household.id == household_id).first()
    if not household:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Household not found"
        )

    # Check if user is a member of this household
    membership = db.query(HouseholdUser).filter(
        HouseholdUser.household_id == household_id,
        HouseholdUser.user_id == current_user.id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this household"
        )

    return household


@router.post("/{household_id}/join")
def join_household(
    household_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Join an existing household."""
    household = db.query(Household).filter(Household.id == household_id).first()
    if not household:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Household not found"
        )

    # Check if user is already a member
    existing_membership = db.query(HouseholdUser).filter(
        HouseholdUser.household_id == household_id,
        HouseholdUser.user_id == current_user.id
    ).first()

    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already a member of this household"
        )

    # Add user to household
    household_user = HouseholdUser(
        household_id=household_id,
        user_id=current_user.id,
        share_default=1.0
    )
    db.add(household_user)
    db.commit()

    return {"message": "Successfully joined household"}


@router.get("/", response_model=List[HouseholdSchema])
def get_user_households(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all households the current user is a member of."""
    households = db.query(Household).join(HouseholdUser).filter(
        HouseholdUser.user_id == current_user.id
    ).all()

    return households