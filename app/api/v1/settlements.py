from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.household import HouseholdUser
from app.models.planning import PlanningWeek
from app.models.settlement import Settlement
from app.schemas.settlement import WeekSettlement
from app.api.deps import get_current_user
from app.models.receipt import Receipt
from datetime import datetime, timedelta

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

    # Calculate time window for the week [week_start, week_start + 7 days)
    start_dt = datetime.combine(week.week_start, datetime.min.time())
    end_dt = start_dt + timedelta(days=7)

    # Get household members and their weights (share_default)
    members = db.query(HouseholdUser).filter(
        HouseholdUser.household_id == week.household_id
    ).all()
    if not members:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No household members found")

    user_ids = [m.user_id for m in members]
    weights = {m.user_id: (m.share_default or 1.0) for m in members}
    total_weight = sum(weights.values()) or 1.0

    # Sum total paid per payer for receipts in the week (completed or any status)
    receipts = db.query(Receipt).filter(
        Receipt.household_id == week.household_id,
        Receipt.purchased_at >= start_dt,
        Receipt.purchased_at < end_dt,
    ).all()

    paid_by = {uid: 0.0 for uid in user_ids}
    total_spend = 0.0
    for r in receipts:
        # Use sum of line prices if available, else omit (could extend to OCR lines)
        receipt_total = 0.0
        for line in r.receipt_lines:
            receipt_total += line.line_price or 0.0
        # If no lines present, we can't infer a total; skip
        if receipt_total <= 0.0:
            continue
        paid_by[r.payer_id] = paid_by.get(r.payer_id, 0.0) + receipt_total
        total_spend += receipt_total

    if total_spend <= 0:
        # Nothing to settle; clear existing settlements for this week
        db.query(Settlement).filter(Settlement.planning_week_id == week_id).delete()
        db.commit()
        return {"message": "No spending found for the week; settlements cleared"}

    # Compute fair share per user by weight
    fair_share = {uid: total_spend * (weights[uid] / total_weight) for uid in user_ids}

    # Compute deltas: positive means overpaid (is owed), negative means owes
    deltas = {uid: paid_by.get(uid, 0.0) - fair_share[uid] for uid in user_ids}

    # Build payers (owed) and payees (owing)
    creditors = [(uid, amt) for uid, amt in deltas.items() if amt > 0.005]
    debtors = [(uid, -amt) for uid, amt in deltas.items() if amt < -0.005]
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)

    # Clear existing settlements
    db.query(Settlement).filter(Settlement.planning_week_id == week_id).delete()

    # Greedy settlement matching
    i, j = 0, 0
    created = 0
    while i < len(debtors) and j < len(creditors):
        debtor_id, owe_amt = debtors[i]
        creditor_id, owed_amt = creditors[j]
        pay = min(owe_amt, owed_amt)

        if pay > 0.0:
            db.add(Settlement(
                planning_week_id=week_id,
                payer_id=debtor_id,
                payee_id=creditor_id,
                amount=round(pay, 2),
            ))
            created += 1

        owe_amt -= pay
        owed_amt -= pay
        debtors[i] = (debtor_id, owe_amt)
        creditors[j] = (creditor_id, owed_amt)
        if owe_amt <= 0.005:
            i += 1
        if owed_amt <= 0.005:
            j += 1

    db.commit()

    return {"message": f"Week settlement closed successfully ({created} entries)"}
