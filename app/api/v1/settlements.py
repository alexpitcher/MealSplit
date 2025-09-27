from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.household import HouseholdUser
from app.models.planning import PlanningWeek
from app.models.settlement import Settlement
from app.schemas.settlement import WeekSettlement
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/weeks/{week_id}/settlement", response_model=WeekSettlement)
def get_week_settlement(
    week_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get settlement summary for a planning week."""
    # Get planning week
    week = db.query(PlanningWeek).filter(PlanningWeek.id == week_id).first()
    if not week:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planning week not found"
        )

    # Verify user is member of household
    membership = db.query(HouseholdUser).filter(
        HouseholdUser.household_id == week.household_id,
        HouseholdUser.user_id == current_user.id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this household"
        )

    # Get settlements for this week
    settlements = db.query(Settlement).filter(
        Settlement.planning_week_id == week_id
    ).all()

    total_amount = sum(settlement.amount for settlement in settlements)

    # Check if settlements are balanced (sum should be close to 0)
    is_balanced = abs(total_amount) < 0.01

    return {
        "planning_week_id": week_id,
        "settlements": settlements,
        "total_amount": total_amount,
        "is_balanced": is_balanced
    }


@router.post("/weeks/{week_id}/close")
def close_week_settlement(
    week_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Close settlements for a planning week and optionally sync to Splitwise."""
    # Get planning week
    week = db.query(PlanningWeek).filter(PlanningWeek.id == week_id).first()
    if not week:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planning week not found"
        )

    # Verify user is member of household
    membership = db.query(HouseholdUser).filter(
        HouseholdUser.household_id == week.household_id,
        HouseholdUser.user_id == current_user.id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this household"
        )

    # TODO: Implement settlement calculation logic
    # 1. Calculate total costs from receipts and matches
    # 2. Determine each member's share based on consumption
    # 3. Create Settlement records
    # 4. Optionally sync to Splitwise

    return {"message": "Week settlement closed successfully"}