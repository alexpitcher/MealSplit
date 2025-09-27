from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.household import HouseholdUser
from app.models.receipt import Receipt, ReceiptLine, LineMatch
from app.schemas.receipt import (
    ReceiptUpload,
    Receipt as ReceiptSchema,
    MatchConfirmation,
    PendingMatches
)
from app.api.deps import get_current_user

router = APIRouter()


@router.post("/", response_model=ReceiptSchema)
async def upload_receipt(
    receipt_data: ReceiptUpload,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a new receipt for OCR processing."""
    # Verify user is member of household
    membership = db.query(HouseholdUser).filter(
        HouseholdUser.household_id == receipt_data.household_id,
        HouseholdUser.user_id == current_user.id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this household"
        )

    # Save uploaded file (implementation depends on storage strategy)
    # For now, just create a placeholder receipt
    db_receipt = Receipt(
        household_id=receipt_data.household_id,
        payer_id=current_user.id,
        store_name=receipt_data.store_name or "Unknown Store",
        purchased_at=receipt_data.purchased_at,
        currency="USD",
        status="pending"
    )
    db.add(db_receipt)
    db.commit()
    db.refresh(db_receipt)

    # TODO: Queue OCR processing job
    # ocr_worker.process_receipt.delay(db_receipt.id, file_path)

    return db_receipt


@router.get("/{receipt_id}", response_model=ReceiptSchema)
def get_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get receipt details."""
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found"
        )

    # Verify user is member of household
    membership = db.query(HouseholdUser).filter(
        HouseholdUser.household_id == receipt.household_id,
        HouseholdUser.user_id == current_user.id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this household"
        )

    return receipt


@router.get("/weeks/{week_id}/matches/pending", response_model=PendingMatches)
def get_pending_matches(
    week_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pending matches for a planning week."""
    # TODO: Implement logic to find unmatched receipt lines
    # and suggested matches for the given planning week

    # Placeholder implementation
    return {
        "receipt_lines": [],
        "suggested_matches": []
    }


@router.post("/matches/{receipt_line_id}/confirm")
def confirm_match(
    receipt_line_id: int,
    match_data: MatchConfirmation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirm a receipt line match."""
    # Get receipt line
    receipt_line = db.query(ReceiptLine).filter(
        ReceiptLine.id == receipt_line_id
    ).first()

    if not receipt_line:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt line not found"
        )

    # Verify user is member of household
    membership = db.query(HouseholdUser).filter(
        HouseholdUser.household_id == receipt_line.receipt.household_id,
        HouseholdUser.user_id == current_user.id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this household"
        )

    # Create or update line match
    existing_match = db.query(LineMatch).filter(
        LineMatch.receipt_line_id == receipt_line_id,
        LineMatch.recipe_ingredient_id == match_data.recipe_ingredient_id
    ).first()

    if existing_match:
        existing_match.qty_consumed = match_data.qty_consumed
        existing_match.price_allocated = match_data.price_allocated
        existing_match.confidence = 1.0  # User confirmed
    else:
        line_match = LineMatch(
            receipt_line_id=receipt_line_id,
            recipe_ingredient_id=match_data.recipe_ingredient_id,
            confidence=1.0,  # User confirmed
            qty_purchased=receipt_line.qty or 1.0,
            qty_consumed=match_data.qty_consumed,
            unit=receipt_line.unit or "unit",
            price_allocated=match_data.price_allocated
        )
        db.add(line_match)

    db.commit()
    return {"message": "Match confirmed successfully"}