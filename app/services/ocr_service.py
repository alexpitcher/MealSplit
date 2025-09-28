import logging
from typing import Dict, Any, List, Optional
import json
import os
import asyncio
import time
from datetime import datetime
import httpx
import aiofiles
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


class OCRService:
    """Service for processing receipt images with OCR using Tabscanner API."""

    def __init__(self):
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.pdf', '.txt', '.json']
        self.api_key = os.getenv("TABSCANNER_API_KEY")
        self.process_endpoint = "https://api.tabscanner.com/api/2/process"
        self.result_endpoint_base = "https://api.tabscanner.com/api/result/"
        self.max_polling_attempts = 60  # Max 60 seconds of polling
        self.polling_interval = 1  # Poll every 1 second

    async def process_receipt_image(self, image_path: str) -> Dict[str, Any]:
        """Process a receipt image and extract structured data using Tabscanner API.

        Development-friendly behavior:
        - If a sidecar JSON exists (same path with .json) or the input is a .json,
          parse it as pre-extracted OCR results and return.
        - If a .txt file is provided, parse simple line-based items.
        - If API key is available, use Tabscanner API for real OCR processing.
        - Otherwise, fall back to a deterministic mock result.
        """
        try:
            # Validate file format
            if not self._is_supported_format(image_path):
                raise ValueError(f"Unsupported file format: {image_path}")

            # 1) Sidecar JSON parsing (preferred in dev/test)
            base, ext = os.path.splitext(image_path)
            json_path = image_path if ext == ".json" else f"{base}.json"
            if os.path.exists(json_path):
                async with aiofiles.open(json_path, "r") as f:
                    content = await f.read()
                    data = json.loads(content)
                return data

            # 2) Simple .txt format parsing
            if ext == ".txt" and os.path.exists(image_path):
                return await self._parse_text_file(image_path)

            # 3) Real Tabscanner API processing
            if self.api_key and ext in ['.jpg', '.jpeg', '.png']:
                logger.info(f"Processing receipt with Tabscanner API: {image_path}")
                return await self._process_with_tabscanner(image_path)

            # 4) Fallback deterministic data
            logger.warning(f"No API key configured, using fallback data for: {image_path}")
            return await self._get_fallback_result()

        except Exception as e:
            logger.error(f"OCR processing failed for {image_path}: {e}")
            raise

    async def _process_with_tabscanner(self, image_path: str) -> Dict[str, Any]:
        """Process receipt using Tabscanner API."""
        try:
            # Upload receipt image
            token = await self._upload_receipt(image_path)
            if not token:
                raise ValueError("Failed to upload receipt to Tabscanner")

            # Poll for results
            result = await self._poll_for_result(token)
            if not result:
                raise ValueError("Failed to get OCR result from Tabscanner")

            # Parse and normalize the result
            return await self._parse_tabscanner_response(result)

        except Exception as e:
            logger.error(f"Tabscanner processing failed: {e}")
            raise

    async def _upload_receipt(self, image_path: str) -> Optional[str]:
        """Upload receipt image to Tabscanner and get token."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with aiofiles.open(image_path, 'rb') as f:
                    file_content = await f.read()

                files = {"file": (os.path.basename(image_path), file_content, "image/jpeg")}
                headers = {"apikey": self.api_key}

                response = await client.post(
                    self.process_endpoint,
                    headers=headers,
                    files=files
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("token")
                else:
                    logger.error(f"Upload failed: {response.status_code} - {response.text}")
                    return None

        except Exception as e:
            logger.error(f"Failed to upload receipt: {e}")
            return None

    async def _poll_for_result(self, token: str) -> Optional[Dict[str, Any]]:
        """Poll Tabscanner for processing results."""
        polling_url = f"{self.result_endpoint_base}{token}"
        headers = {"apikey": self.api_key}

        for attempt in range(self.max_polling_attempts):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(polling_url, headers=headers)

                    if response.status_code == 200:
                        result_data = response.json()
                        status = result_data.get("status")

                        if status == "done":
                            return result_data.get("result")
                        elif status == "pending":
                            logger.info(f"OCR processing in progress... (attempt {attempt + 1})")
                            await asyncio.sleep(self.polling_interval)
                        else:
                            logger.error(f"OCR processing failed with status: {status}")
                            return None
                    else:
                        logger.error(f"Polling failed: {response.status_code} - {response.text}")
                        return None

            except Exception as e:
                logger.error(f"Polling attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(self.polling_interval)

        logger.error("OCR processing timed out")
        return None

    async def _parse_tabscanner_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Tabscanner API response into our standard format."""
        try:
            # Handle empty or malformed responses
            if not response or not isinstance(response, dict):
                logger.warning("Empty or malformed Tabscanner response, using fallback")
                return await self._get_fallback_result()

            # Extract basic receipt info with better fallbacks
            merchant_info = response.get("merchant", {})
            store_name = merchant_info.get("name") if merchant_info else None
            if not store_name:
                # Try alternative field names
                store_name = response.get("store_name") or response.get("storeName") or "Unknown Store"

            # Handle date parsing
            purchase_date = response.get("date")
            if not purchase_date:
                purchase_date = response.get("purchase_date") or response.get("timestamp")
            if not purchase_date:
                purchase_date = datetime.now().isoformat()

            currency = response.get("currency", "GBP")  # Default to GBP for UK receipts
            total_amount = self._safe_decimal(response.get("total"))

            # Extract line items with multiple fallback strategies
            items = []
            raw_items = response.get("lineItems", [])

            # Try alternative field names if lineItems is empty
            if not raw_items:
                raw_items = response.get("items", []) or response.get("products", []) or []

            for item in raw_items:
                if not isinstance(item, dict):
                    continue

                # Try multiple field names for item description
                name = (item.get("desc") or item.get("description") or
                       item.get("name") or item.get("product") or "").strip()

                if not name or len(name) < 2:  # Skip very short or empty names
                    continue

                # Clean up common OCR artifacts
                name = self._clean_item_name(name)

                qty, unit = self.extract_quantity_and_unit(name)

                # Try multiple field names for prices
                unit_price = (self._safe_decimal(item.get("unitPrice")) or
                             self._safe_decimal(item.get("unit_price")) or
                             self._safe_decimal(item.get("price")))

                total_price = (self._safe_decimal(item.get("amount")) or
                              self._safe_decimal(item.get("total")) or
                              self._safe_decimal(item.get("lineTotal")))

                # If we have total but no unit price, calculate it
                if total_price and not unit_price and qty and qty > 0:
                    unit_price = total_price / qty
                elif unit_price and not total_price and qty:
                    total_price = unit_price * qty

                # Default to unit price if no total
                if not total_price:
                    total_price = unit_price or 0.0

                items.append({
                    "name": name,
                    "quantity": qty,
                    "unit": unit,
                    "unit_price": unit_price,
                    "total_price": total_price,
                    "confidence": 0.95,  # Tabscanner is generally very accurate
                    "raw_item": item  # Keep raw for debugging
                })

            # Calculate total if not provided
            if not total_amount and items:
                total_amount = sum(item.get("total_price", 0) for item in items)

            return {
                "store_name": store_name,
                "purchase_date": purchase_date,
                "currency": currency,
                "total_amount": total_amount or 0.0,
                "items": items,
                "metadata": {
                    "ocr_engine": "tabscanner",
                    "confidence_avg": 0.95,
                    "items_processed": len(items),
                    "raw_response": response  # Keep for debugging
                }
            }

        except Exception as e:
            logger.error(f"Failed to parse Tabscanner response: {e}")
            logger.error(f"Response was: {response}")
            # Return a fallback result rather than failing completely
            return await self._get_fallback_result()

    def _clean_item_name(self, name: str) -> str:
        """Clean up common OCR artifacts in item names."""
        if not name:
            return ""

        # Remove common OCR artifacts
        name = name.replace("'", "'")  # Fix apostrophes
        name = name.replace(""", '"').replace(""", '"')  # Fix quotes
        name = name.replace("–", "-").replace("—", "-")  # Fix dashes

        # Remove leading/trailing punctuation that doesn't belong
        name = name.strip(" .,;:-_")

        # Remove multiple spaces
        import re
        name = re.sub(r'\s+', ' ', name)

        return name

    def _safe_decimal(self, value) -> Optional[float]:
        """Safely convert value to decimal/float."""
        if value is None:
            return None
        try:
            if isinstance(value, str):
                # Remove currency symbols and extra spaces
                value = value.replace("£", "").replace("$", "").replace("€", "").strip()
            return float(Decimal(str(value)))
        except (InvalidOperation, ValueError, TypeError):
            return None

    async def _parse_text_file(self, image_path: str) -> Dict[str, Any]:
        """Parse simple .txt format receipts."""
        items: List[Dict[str, Any]] = []

        async with aiofiles.open(image_path, "r") as f:
            async for line in f:
                line = line.strip()
                if not line:
                    continue

                qty, unit = self.extract_quantity_and_unit(line)
                unit_price = None
                total_price = None

                # Try to parse prices with simple patterns
                try:
                    if "@" in line and "=" in line:
                        after_at = line.split("@", 1)[1]
                        left_price = after_at.split("=", 1)[0].strip()
                        unit_price = float(left_price.split()[0])
                        right_total = after_at.split("=", 1)[1].strip()
                        total_price = float(right_total.split()[0])
                    else:
                        # Try last number as total
                        tokens = [t for t in line.replace("=", " ").split() if t]
                        floats = [float(t) for t in tokens if t.replace('.', '', 1).isdigit()]
                        if floats:
                            total_price = floats[-1]
                except Exception:
                    pass

                items.append({
                    "name": line,
                    "quantity": qty,
                    "unit": unit,
                    "unit_price": unit_price,
                    "total_price": total_price if total_price is not None else unit_price or 0.0,
                    "confidence": 0.75,
                })

        return {
            "store_name": "Text Import",
            "purchase_date": datetime.now().isoformat(),
            "currency": "USD",
            "total_amount": sum(i.get("total_price") or 0.0 for i in items),
            "items": items,
            "metadata": {"ocr_engine": "text-parser", "confidence_avg": 0.75},
        }

    async def _get_fallback_result(self) -> Dict[str, Any]:
        """Get deterministic fallback result for development."""
        return {
            "store_name": "Fallback Store",
            "purchase_date": datetime.now().isoformat(),
            "currency": "USD",
            "total_amount": 45.67,
            "items": [
                {
                    "name": "Organic Bananas",
                    "quantity": 2.5,
                    "unit": "lb",
                    "unit_price": 1.99,
                    "total_price": 4.98,
                    "confidence": 0.95
                },
                {
                    "name": "Whole Milk",
                    "quantity": 1,
                    "unit": "gallon",
                    "unit_price": 3.49,
                    "total_price": 3.49,
                    "confidence": 0.88
                }
            ],
            "metadata": {
                "processing_time": 2.3,
                "ocr_engine": "fallback",
                "confidence_avg": 0.915
            }
        }

    def _is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported."""
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.supported_formats

    def normalize_item_name(self, raw_name: str) -> str:
        """Normalize item names for better matching.

        Steps:
        - Lowercase and trim whitespace
        - Remove promotional phrases (e.g., BOGO, sale)
        - Standardize common units/abbreviations
        - Drop common brand words and descriptors
        - Collapse extra spaces
        """
        import re

        if not raw_name:
            return ""

        text = raw_name.lower().strip()

        # Remove promotional patterns
        promo_patterns = [r"\b(bogo|sale|promo|special|club price)\b", r"\b(x?\d+/?\d+ off)\b"]
        for pat in promo_patterns:
            text = re.sub(pat, " ", text)

        # Standardize units/abbreviations
        replacements = {
            " oz.": " oz",
            " fl oz": " floz",
            " fl. oz": " floz",
            " ounce": " oz",
            " ounces": " oz",
            " lbs": " lb",
            " pound": " lb",
            " pounds": " lb",
            " g ": " gram ",
            " kg ": " kilogram ",
            " qty ": " ",
            "%": " percent",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)

        # Remove brand names/descriptors (lightweight list)
        brand_words = [
            "organic", "brand", "select", "signature", "great value", "market pantry",
            "kirkland", "trader joe's", "trader joes", "whole foods", "365",
            "vitamin d", "2 percent", "2percent", "fat free", "reduced fat",
        ]
        for w in brand_words:
            text = text.replace(w, " ")

        # Remove punctuation except alphanumerics and space
        text = re.sub(r"[^a-z0-9\s]", " ", text)

        # Collapse whitespace
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def extract_quantity_and_unit(self, item_text: str) -> tuple[Optional[float], Optional[str]]:
        """Extract quantity and unit from item text using regex patterns.

        Supports patterns like:
        - "2.5 lb", "1 gallon", "6 pack", "12 oz", "3 x 12 oz"
        Returns (quantity, unit) or (1.0, "unit") if not found.
        """
        import re

        if not item_text:
            return 1.0, "unit"

        text = item_text.lower()

        # Try composite like "3 x 12 oz" => quantity 12, unit oz (assume overall qty is 12 oz)
        m = re.search(r"(\d+(?:\.\d+)?)\s*[x\*]\s*(\d+(?:\.\d+)?)\s*(oz|lb|g|kg|ml|l|pack|ct|gallon)s?\b", text)
        if m:
            count = float(m.group(1))
            qty = float(m.group(2))
            unit = m.group(3)
            return qty, unit

        # Standard quantity+unit
        m = re.search(r"(\d+(?:\.\d+)?)\s*(gallon|gal|oz|floz|lb|kg|g|mg|ml|l|pack|ct)s?\b", text)
        if m:
            qty = float(m.group(1))
            unit = m.group(2)
            # Normalize some units
            unit_map = {"gal": "gallon", "floz": "floz", "ct": "count"}
            unit = unit_map.get(unit, unit)
            return qty, unit

        # Pack only
        m = re.search(r"(\d+(?:\.\d+)?)\s*(pack|count|ct)\b", text)
        if m:
            return float(m.group(1)), "count"

        # Fallback
        return 1.0, "unit"
