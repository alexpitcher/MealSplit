from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class UnitConversion(Base):
    """Unit conversion lookup table for normalizing measurements."""
    __tablename__ = "unit_conversions"

    id = Column(Integer, primary_key=True, index=True)
    from_unit = Column(String, nullable=False, index=True)
    to_unit = Column(String, nullable=False)
    multiplier = Column(Float, nullable=False)
    unit_type = Column(String, nullable=False)  # weight, volume, count, etc.


class UserMatchConfirmation(Base):
    """Store user confirmations for learning algorithm improvements."""
    __tablename__ = "user_match_confirmations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receipt_text = Column(String, nullable=False)
    normalized_text = Column(String, nullable=False)
    ingredient_id = Column(Integer, ForeignKey("recipe_ingredients.id"), nullable=False)
    confidence_score = Column(Float, nullable=False)
    was_correct = Column(Boolean, nullable=False)
    confirmed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User")
    ingredient = relationship("RecipeIngredient")


class IngredientSynonym(Base):
    """Store ingredient synonyms and variations for better matching."""
    __tablename__ = "ingredient_synonyms"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("recipe_ingredients.id"), nullable=False)
    synonym = Column(String, nullable=False, index=True)
    normalized_synonym = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False)  # user, system, import
    confidence = Column(Float, nullable=False, default=1.0)

    # Relationships
    ingredient = relationship("RecipeIngredient")