from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    payer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    store_name = Column(String, nullable=False)
    purchased_at = Column(DateTime(timezone=True), nullable=False)
    currency = Column(String, nullable=False, default="USD")
    image_ref = Column(String)  # Path or URL to receipt image
    ocr_json_ref = Column(String)  # Path or URL to OCR results JSON
    status = Column(String, nullable=False, default="pending")  # pending, processing, completed, failed

    # Relationships
    household = relationship("Household", back_populates="receipts")
    payer = relationship("User", back_populates="receipts")
    receipt_lines = relationship("ReceiptLine", back_populates="receipt")


class ReceiptLine(Base):
    __tablename__ = "receipt_lines"

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id"), nullable=False)
    raw_text = Column(String, nullable=False)
    normalized_name = Column(String)
    qty = Column(Float)
    unit = Column(String)
    unit_price = Column(Float)
    line_price = Column(Float, nullable=False)
    promo_applied = Column(Boolean, default=False)
    meta = Column(JSON)  # Additional OCR metadata

    # Relationships
    receipt = relationship("Receipt", back_populates="receipt_lines")
    line_matches = relationship("LineMatch", back_populates="receipt_line")


class LineMatch(Base):
    __tablename__ = "line_matches"

    id = Column(Integer, primary_key=True, index=True)
    receipt_line_id = Column(Integer, ForeignKey("receipt_lines.id"), nullable=False)
    recipe_ingredient_id = Column(Integer, ForeignKey("recipe_ingredients.id"), nullable=False)
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    qty_purchased = Column(Float, nullable=False)
    qty_consumed = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    price_allocated = Column(Float, nullable=False)

    # Relationships
    receipt_line = relationship("ReceiptLine", back_populates="line_matches")
    recipe_ingredient = relationship("RecipeIngredient", back_populates="line_matches")