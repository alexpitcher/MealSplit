from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class ReceiptLineBase(BaseModel):
    raw_text: str
    normalized_name: Optional[str] = None
    qty: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    line_price: float
    promo_applied: bool = False
    meta: Optional[Dict[str, Any]] = None


class ReceiptLineCreate(ReceiptLineBase):
    pass


class ReceiptLine(ReceiptLineBase):
    id: int
    receipt_id: int

    class Config:
        from_attributes = True


class ReceiptBase(BaseModel):
    household_id: int
    store_name: str
    purchased_at: datetime
    currency: str = "USD"


class ReceiptCreate(ReceiptBase):
    lines: List[ReceiptLineCreate] = []


class ReceiptUpload(BaseModel):
    household_id: int
    store_name: Optional[str] = None
    purchased_at: Optional[datetime] = None


class Receipt(ReceiptBase):
    id: int
    payer_id: int
    image_ref: Optional[str] = None
    ocr_json_ref: Optional[str] = None
    status: str
    receipt_lines: List[ReceiptLine] = []

    class Config:
        from_attributes = True


class LineMatchBase(BaseModel):
    receipt_line_id: int
    recipe_ingredient_id: int
    confidence: float
    qty_purchased: float
    qty_consumed: float
    unit: str
    price_allocated: float


class LineMatchCreate(LineMatchBase):
    pass


class LineMatch(LineMatchBase):
    id: int

    class Config:
        from_attributes = True


class MatchConfirmation(BaseModel):
    receipt_line_id: int
    recipe_ingredient_id: int
    qty_consumed: float
    price_allocated: float


class PendingMatches(BaseModel):
    receipt_lines: List[ReceiptLine]
    suggested_matches: List[LineMatch]