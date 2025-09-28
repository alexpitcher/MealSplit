from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Form
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os
import asyncio

from app.core.database import get_db
from app.core.config import settings
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
from app.workers.ocr_worker import OCRWorker
from app.services.matching_service import MatchingService
from app.services.advanced_matching_service import AdvancedMatchingService

router = APIRouter()


@router.post("/", response_model=ReceiptSchema)
async def upload_receipt(
    file: UploadFile = File(...),
    household_id: int = Form(...),
    store_name: str | None = Form(None),
    purchased_at: datetime | None = Form(None),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a new receipt for OCR processing."""
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

    # Create a new receipt record
    if not purchased_at:
        purchased_at = datetime.utcnow()

    db_receipt = Receipt(
        household_id=household_id,
        payer_id=current_user.id,
        store_name=store_name or "Unknown Store",
        purchased_at=purchased_at,
        currency="USD",
        status="pending"
    )
    db.add(db_receipt)
    db.commit()
    db.refresh(db_receipt)

    # Save uploaded file to storage
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower() if ext else ".jpg"
    file_path = os.path.join(upload_dir, f"receipt_{db_receipt.id}{ext}")
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Update receipt with image reference
    db_receipt.image_ref = file_path
    db.commit()
    db.refresh(db_receipt)

    # Schedule OCR processing in background
    ocr_worker = OCRWorker()
    if background_tasks is not None:
        background_tasks.add_task(ocr_worker.process_receipt, db_receipt.id, file_path)

    return db_receipt


@router.get("/", response_model=List[dict])
def list_receipts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List recent receipts for households the user belongs to.

    Returns a simplified shape expected by the web UI.
    """
    # Get household ids for current user
    household_ids = [m.household_id for m in db.query(HouseholdUser).filter(HouseholdUser.user_id == current_user.id).all()]
    if not household_ids:
        return []

    # Fetch recent receipts
    receipts = db.query(Receipt).filter(Receipt.household_id.in_(household_ids)).order_by(Receipt.purchased_at.desc()).limit(50).all()

    result = []
    for r in receipts:
        # Compute total from lines if available
        total_amount = sum((line.line_price or 0.0) for line in (r.receipt_lines or []))
        result.append({
            "id": r.id,
            "filename": os.path.basename(r.image_ref) if r.image_ref else f"receipt_{r.id}",
            "upload_date": r.purchased_at.isoformat() if r.purchased_at else None,
            "total_amount": total_amount,
            "store_name": r.store_name,
            "ocr_status": r.status,
            "user_id": r.payer_id,
        })

    return result


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
    # Find unmatched receipt lines within the planning week timeframe
    from app.models.planning import PlanningWeek
    week = db.query(PlanningWeek).filter(PlanningWeek.id == week_id).first()
    if not week:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planning week not found")

    # Verify user is member of household
    membership = db.query(HouseholdUser).filter(
        HouseholdUser.household_id == week.household_id,
        HouseholdUser.user_id == current_user.id,
    ).first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this household")

    start_dt = datetime.combine(week.week_start, datetime.min.time())
    end_dt = start_dt + timedelta(days=7)

    # Get unmatched receipt lines for receipts in this time window
    receipt_lines = (
        db.query(ReceiptLine)
        .join(Receipt)
        .filter(
            Receipt.household_id == week.household_id,
            Receipt.purchased_at >= start_dt,
            Receipt.purchased_at < end_dt,
            ~ReceiptLine.line_matches.any(),
        )
        .all()
    )

    # Generate suggestions using MatchingService
    matcher = MatchingService()
    suggested_matches = []
    for rl in receipt_lines:
        suggestions = matcher.find_matches_for_receipt_line(db, rl, week_id)
        # Convert suggestions to LineMatch-shaped dicts (id=0 for suggestions)
        for s in suggestions[:3]:
            suggested_matches.append({
                "id": 0,
                "receipt_line_id": rl.id,
                "recipe_ingredient_id": s["recipe_ingredient_id"],
                "confidence": s["confidence"],
                "qty_purchased": rl.qty or 1.0,
                "qty_consumed": s["suggested_qty_consumed"],
                "unit": rl.unit or "unit",
                "price_allocated": s["suggested_price"],
            })

    return {"receipt_lines": receipt_lines, "suggested_matches": suggested_matches}


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


@router.get("/{receipt_id}/matches/pending", response_model=dict)
def get_receipt_pending_matches(
    receipt_id: int,
    week_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pending matches for a specific receipt using advanced matching."""
    # Get the receipt
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

    # Get unmatched receipt lines
    unmatched_lines = db.query(ReceiptLine).filter(
        ReceiptLine.receipt_id == receipt_id,
        ~ReceiptLine.line_matches.any()
    ).all()

    # Enforce AI (Gemini) configured
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="AI matching (Gemini) is required but not configured")

    # Use advanced matching service
    advanced_matcher = AdvancedMatchingService()
    matches_data = []

    # Auto-match high confidence first
    for line in unmatched_lines:
        try:
            advanced_matcher.auto_match_high_confidence(db, line, planning_week_id=1)
        except Exception:
            continue

    # Refresh unmatched lines post auto-match
    unmatched_lines = db.query(ReceiptLine).filter(
        ReceiptLine.receipt_id == receipt_id,
        ~ReceiptLine.line_matches.any()
    ).all()

    for line in unmatched_lines:
        # Find matches for the specified planning week
        matches = advanced_matcher.find_matches_for_receipt_line(db, line, week_id=week_id)

        line_data = {
            "receipt_line": {
                "id": line.id,
                "raw_text": line.raw_text,
                "normalized_name": line.normalized_name,
                "qty": line.qty,
                "unit": line.unit,
                "line_price": line.line_price
            },
            "suggested_matches": matches[:5]  # Top 5 matches
        }
        matches_data.append(line_data)

    return {
        "receipt_id": receipt_id,
        "store_name": receipt.store_name,
        "purchased_at": receipt.purchased_at.isoformat() if receipt.purchased_at else None,
        "unmatched_lines": matches_data,
        "total_unmatched": len(unmatched_lines)
    }


@router.post("/lines/{receipt_line_id}/match", response_model=dict)
def create_manual_match(
    receipt_line_id: int,
    match_data: MatchConfirmation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a manual match with learning feedback."""
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

    # Create the match
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
    db.refresh(line_match)

    # Store learning feedback
    advanced_matcher = AdvancedMatchingService()
    advanced_matcher.confirm_match(
        db=db,
        user_id=current_user.id,
        receipt_line_id=receipt_line_id,
        ingredient_id=match_data.recipe_ingredient_id,
        was_correct=True
    )

    return {
        "message": "Match created successfully",
        "match_id": line_match.id,
        "learning_stored": True
    }


@router.post("/lines/{receipt_line_id}/reject", response_model=dict)
def reject_suggested_match(
    receipt_line_id: int,
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject a suggested match for learning purposes."""
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

    # Store negative feedback for learning
    advanced_matcher = AdvancedMatchingService()
    advanced_matcher.confirm_match(
        db=db,
        user_id=current_user.id,
        receipt_line_id=receipt_line_id,
        ingredient_id=ingredient_id,
        was_correct=False
    )

    return {
        "message": "Match rejection recorded",
        "learning_stored": True
    }


@router.get("/{receipt_id}/matching-stats", response_model=dict)
def get_matching_statistics(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get matching statistics for a receipt."""
    # Get the receipt
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

    # Calculate statistics
    total_lines = db.query(ReceiptLine).filter(ReceiptLine.receipt_id == receipt_id).count()
    matched_lines = db.query(ReceiptLine).filter(
        ReceiptLine.receipt_id == receipt_id,
        ReceiptLine.line_matches.any()
    ).count()

    unmatched_lines = total_lines - matched_lines
    match_rate = (matched_lines / total_lines * 100) if total_lines > 0 else 0

    # Get confidence distribution
    matches = db.query(LineMatch).join(ReceiptLine).filter(
        ReceiptLine.receipt_id == receipt_id
    ).all()

    confidence_stats = {
        "high_confidence": len([m for m in matches if m.confidence >= 0.9]),
        "medium_confidence": len([m for m in matches if 0.7 <= m.confidence < 0.9]),
        "low_confidence": len([m for m in matches if m.confidence < 0.7]),
    }

    return {
        "receipt_id": receipt_id,
        "total_lines": total_lines,
        "matched_lines": matched_lines,
        "unmatched_lines": unmatched_lines,
        "match_rate_percent": round(match_rate, 1),
        "confidence_distribution": confidence_stats,
        "needs_review": unmatched_lines > 0 or confidence_stats["low_confidence"] > 0
    }
