import logging
from typing import List
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.redis_client import redis_client
from app.models.receipt import Receipt, ReceiptLine
from app.models.planning import PlanningWeek
from app.services.matching_service import MatchingService

logger = logging.getLogger(__name__)


class MatchingWorker:
    """Background worker for matching receipt items to recipe ingredients."""

    def __init__(self):
        self.matching_service = MatchingService()

    async def process_receipt_matching(
        self,
        receipt_id: int,
        planning_week_id: int
    ) -> bool:
        """Process automatic matching for a receipt against a planning week."""
        db = SessionLocal()
        try:
            # Get receipt and validate
            receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
            if not receipt:
                logger.error(f"Receipt {receipt_id} not found")
                return False

            if receipt.status != "completed":
                logger.warning(f"Receipt {receipt_id} not ready for matching (status: {receipt.status})")
                return False

            # Get planning week and validate
            planning_week = db.query(PlanningWeek).filter(
                PlanningWeek.id == planning_week_id
            ).first()

            if not planning_week:
                logger.error(f"Planning week {planning_week_id} not found")
                return False

            if planning_week.household_id != receipt.household_id:
                logger.error(
                    f"Receipt {receipt_id} household {receipt.household_id} "
                    f"doesn't match planning week household {planning_week.household_id}"
                )
                return False

            # Get receipt lines
            receipt_lines = db.query(ReceiptLine).filter(
                ReceiptLine.receipt_id == receipt_id
            ).all()

            if not receipt_lines:
                logger.info(f"No receipt lines found for receipt {receipt_id}")
                return True

            # Process each receipt line
            matched_count = 0
            total_lines = len(receipt_lines)

            for receipt_line in receipt_lines:
                try:
                    # Attempt automatic matching
                    match = self.matching_service.auto_match_high_confidence(
                        db, receipt_line, planning_week_id
                    )

                    if match:
                        matched_count += 1
                        logger.info(
                            f"Auto-matched receipt line {receipt_line.id} "
                            f"with confidence {match.confidence}"
                        )

                except Exception as e:
                    logger.error(f"Failed to process receipt line {receipt_line.id}: {e}")
                    continue

            # Publish matching results
            await self._publish_matching_results(
                receipt_id, planning_week_id, matched_count, total_lines
            )

            logger.info(
                f"Completed matching for receipt {receipt_id}: "
                f"{matched_count}/{total_lines} lines auto-matched"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to process matching for receipt {receipt_id}: {e}")
            return False

        finally:
            db.close()

    async def suggest_matches_for_week(self, planning_week_id: int) -> bool:
        """Generate match suggestions for all unmatched receipt lines in a week."""
        db = SessionLocal()
        try:
            # Get all receipts for the household and week timeframe
            planning_week = db.query(PlanningWeek).filter(
                PlanningWeek.id == planning_week_id
            ).first()

            if not planning_week:
                logger.error(f"Planning week {planning_week_id} not found")
                return False

            # Get unmatched receipt lines from the household
            # This is a simplified query - in practice you'd want to filter by date range
            unmatched_lines = db.query(ReceiptLine).join(Receipt).filter(
                Receipt.household_id == planning_week.household_id,
                ~ReceiptLine.line_matches.any()  # Lines without matches
            ).all()

            suggestions_generated = 0

            for receipt_line in unmatched_lines:
                try:
                    # Generate match suggestions
                    suggestions = self.matching_service.find_matches_for_receipt_line(
                        db, receipt_line, planning_week_id
                    )

                    if suggestions:
                        suggestions_generated += len(suggestions)

                        # Store suggestions in Redis for frontend retrieval
                        await self._store_match_suggestions(
                            receipt_line.id, planning_week_id, suggestions
                        )

                except Exception as e:
                    logger.error(f"Failed to generate suggestions for line {receipt_line.id}: {e}")
                    continue

            logger.info(
                f"Generated {suggestions_generated} match suggestions "
                f"for planning week {planning_week_id}"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to generate suggestions for week {planning_week_id}: {e}")
            return False

        finally:
            db.close()

    async def _publish_matching_results(
        self,
        receipt_id: int,
        planning_week_id: int,
        matched_count: int,
        total_lines: int
    ):
        """Publish matching completion results."""
        message = {
            "receipt_id": receipt_id,
            "planning_week_id": planning_week_id,
            "matched_count": matched_count,
            "total_lines": total_lines,
            "completion_rate": matched_count / total_lines if total_lines > 0 else 0,
            "timestamp": "now"  # Would use actual timestamp
        }

        channel = f"receipt:{receipt_id}:matching"
        redis_client.publish(channel, str(message))

    async def _store_match_suggestions(
        self,
        receipt_line_id: int,
        planning_week_id: int,
        suggestions: List[dict]
    ):
        """Store match suggestions in Redis for frontend retrieval."""
        key = f"match_suggestions:{receipt_line_id}:{planning_week_id}"

        # Store suggestions for 24 hours
        redis_client.set(key, str(suggestions), ex=86400)

    async def reprocess_week_matching(self, planning_week_id: int) -> bool:
        """Reprocess matching for all receipts in a planning week."""
        db = SessionLocal()
        try:
            planning_week = db.query(PlanningWeek).filter(
                PlanningWeek.id == planning_week_id
            ).first()

            if not planning_week:
                return False

            # Get all completed receipts for the household
            receipts = db.query(Receipt).filter(
                Receipt.household_id == planning_week.household_id,
                Receipt.status == "completed"
            ).all()

            processed_count = 0

            for receipt in receipts:
                success = await self.process_receipt_matching(
                    receipt.id, planning_week_id
                )
                if success:
                    processed_count += 1

            logger.info(
                f"Reprocessed matching for {processed_count} receipts "
                f"in planning week {planning_week_id}"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to reprocess week matching: {e}")
            return False

        finally:
            db.close()