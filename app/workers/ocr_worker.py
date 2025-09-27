import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.redis_client import redis_client
from app.models.receipt import Receipt, ReceiptLine
from app.services.ocr_service import OCRService

logger = logging.getLogger(__name__)


class OCRWorker:
    """Background worker for processing receipt OCR."""

    def __init__(self):
        self.ocr_service = OCRService()

    async def process_receipt(self, receipt_id: int, image_path: str) -> bool:
        """Process a receipt image with OCR."""
        db = SessionLocal()
        try:
            # Get receipt from database
            receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
            if not receipt:
                logger.error(f"Receipt {receipt_id} not found")
                return False

            # Update status to processing
            receipt.status = "processing"
            db.commit()

            # Publish status update
            await self._publish_status_update(receipt_id, "processing")

            # Process image with OCR
            ocr_result = await self.ocr_service.process_receipt_image(image_path)

            # Update receipt with OCR results
            receipt.store_name = ocr_result.get("store_name", receipt.store_name)
            receipt.purchased_at = ocr_result.get("purchase_date", receipt.purchased_at)
            receipt.currency = ocr_result.get("currency", receipt.currency)

            # Save OCR JSON reference (would typically be a file path or S3 URL)
            receipt.ocr_json_ref = f"ocr_results/{receipt_id}.json"

            # Create receipt lines from OCR results
            for item in ocr_result.get("items", []):
                receipt_line = ReceiptLine(
                    receipt_id=receipt_id,
                    raw_text=item.get("name", ""),
                    normalized_name=self.ocr_service.normalize_item_name(item.get("name", "")),
                    qty=item.get("quantity"),
                    unit=item.get("unit"),
                    unit_price=item.get("unit_price"),
                    line_price=item.get("total_price", 0),
                    meta={"confidence": item.get("confidence", 0)}
                )
                db.add(receipt_line)

            # Update status to completed
            receipt.status = "completed"
            db.commit()

            # Publish completion status
            await self._publish_status_update(receipt_id, "completed", ocr_result)

            logger.info(f"Successfully processed receipt {receipt_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to process receipt {receipt_id}: {e}")

            # Update status to failed
            if receipt:
                receipt.status = "failed"
                db.commit()
                await self._publish_status_update(receipt_id, "failed", {"error": str(e)})

            return False

        finally:
            db.close()

    async def _publish_status_update(
        self,
        receipt_id: int,
        status: str,
        data: Dict[str, Any] = None
    ):
        """Publish receipt processing status update."""
        message = {
            "receipt_id": receipt_id,
            "status": status,
            "timestamp": "now",  # Would use actual timestamp
            "data": data or {}
        }

        channel = f"receipt:{receipt_id}:status"
        redis_client.publish(channel, str(message))

    def retry_failed_receipt(self, receipt_id: int) -> bool:
        """Retry processing a failed receipt."""
        db = SessionLocal()
        try:
            receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
            if not receipt:
                return False

            if receipt.status != "failed":
                logger.warning(f"Receipt {receipt_id} is not in failed status")
                return False

            # Clear previous receipt lines
            db.query(ReceiptLine).filter(ReceiptLine.receipt_id == receipt_id).delete()

            # Reset status and retry
            receipt.status = "pending"
            db.commit()

            # Queue for reprocessing
            # In a real implementation, this would use a job queue like Celery
            # celery_app.send_task("process_receipt", args=[receipt_id, receipt.image_ref])

            return True

        except Exception as e:
            logger.error(f"Failed to retry receipt {receipt_id}: {e}")
            return False

        finally:
            db.close()