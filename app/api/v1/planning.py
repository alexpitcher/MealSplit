from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.household import HouseholdUser
from app.models.planning import PlanningWeek, WeekRecipe, ShoppingItem
from app.schemas.planning import (
    PlanningWeekCreate,
    PlanningWeek as PlanningWeekSchema,
    WeekRecipeCreate,
    WeekRecipe as WeekRecipeSchema,
    ShoppingList
)
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/weeks", response_model=List[PlanningWeekSchema])
def get_planning_weeks(
    household_id: int = Query(...),
    start: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get planning weeks for a household."""
    # Verify user is member of household
    membership = db.query(HouseholdUser).filter(
        HouseholdUser.household_id == household_id,
        HouseholdUser.user_id == current_user.id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this household"
        )

    query = db.query(PlanningWeek).filter(PlanningWeek.household_id == household_id)

    if start:
        query = query.filter(PlanningWeek.week_start >= start)

    weeks = query.order_by(PlanningWeek.week_start).all()
    return weeks


@router.post("/weeks", response_model=PlanningWeekSchema)
def create_planning_week(
    week_in: PlanningWeekCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new planning week."""
    # Verify user is member of household
    membership = db.query(HouseholdUser).filter(
        HouseholdUser.household_id == week_in.household_id,
        HouseholdUser.user_id == current_user.id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this household"
        )

    # Check if week already exists
    existing_week = db.query(PlanningWeek).filter(
        PlanningWeek.household_id == week_in.household_id,
        PlanningWeek.week_start == week_in.week_start
    ).first()

    if existing_week:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Planning week already exists for this date"
        )

    db_week = PlanningWeek(**week_in.dict())
    db.add(db_week)
    db.commit()
    db.refresh(db_week)

    return db_week


@router.post("/weeks/{week_id}/recipes", response_model=WeekRecipeSchema)
def add_recipe_to_week(
    week_id: int,
    recipe_in: WeekRecipeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a recipe to a planning week."""
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

    # Add recipe to week
    week_recipe = WeekRecipe(
        planning_week_id=week_id,
        recipe_id=recipe_in.recipe_id,
        planned_servings=recipe_in.planned_servings
    )
    db.add(week_recipe)
    db.commit()
    db.refresh(week_recipe)

    return week_recipe


@router.get("/weeks/{week_id}/shopping-list", response_model=ShoppingList)
def get_shopping_list(
    week_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get shopping list for a planning week."""
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

    # Get shopping items
    shopping_items = db.query(ShoppingItem).filter(
        ShoppingItem.planning_week_id == week_id
    ).all()

    return {
        "planning_week_id": week_id,
        "items": shopping_items
    }