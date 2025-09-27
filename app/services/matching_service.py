import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from difflib import SequenceMatcher

from app.models.planning import RecipeIngredient, PlanningWeek
from app.models.receipt import ReceiptLine, LineMatch

logger = logging.getLogger(__name__)


class MatchingService:
    """Service for matching receipt items to recipe ingredients."""

    def __init__(self):
        self.confidence_threshold = 0.7
        self.exact_match_threshold = 0.95

    def find_matches_for_receipt_line(
        self,
        db: Session,
        receipt_line: ReceiptLine,
        planning_week_id: int
    ) -> List[Dict[str, Any]]:
        """Find potential matches for a receipt line against recipe ingredients."""

        # Get all recipe ingredients for the planning week
        recipe_ingredients = self._get_week_ingredients(db, planning_week_id)

        matches = []
        normalized_receipt_name = self._normalize_name(receipt_line.normalized_name or receipt_line.raw_text)

        for ingredient in recipe_ingredients:
            normalized_ingredient_name = self._normalize_name(ingredient.name)

            # Calculate similarity score
            confidence = self._calculate_similarity(
                normalized_receipt_name,
                normalized_ingredient_name
            )

            if confidence >= self.confidence_threshold:
                match_data = self._create_match_suggestion(
                    receipt_line,
                    ingredient,
                    confidence
                )
                matches.append(match_data)

        # Sort by confidence descending
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        return matches

    def auto_match_high_confidence(
        self,
        db: Session,
        receipt_line: ReceiptLine,
        planning_week_id: int
    ) -> Optional[LineMatch]:
        """Automatically create matches for high-confidence suggestions."""

        matches = self.find_matches_for_receipt_line(db, receipt_line, planning_week_id)

        if not matches:
            return None

        best_match = matches[0]
        if best_match['confidence'] >= self.exact_match_threshold:
            # Create automatic match
            line_match = LineMatch(
                receipt_line_id=receipt_line.id,
                recipe_ingredient_id=best_match['recipe_ingredient_id'],
                confidence=best_match['confidence'],
                qty_purchased=receipt_line.qty or 1.0,
                qty_consumed=best_match['suggested_qty_consumed'],
                unit=receipt_line.unit or "unit",
                price_allocated=best_match['suggested_price']
            )

            db.add(line_match)
            db.commit()
            db.refresh(line_match)

            logger.info(
                f"Auto-matched receipt line {receipt_line.id} to ingredient "
                f"{best_match['recipe_ingredient_id']} with confidence {best_match['confidence']}"
            )

            return line_match

        return None

    def _get_week_ingredients(self, db: Session, planning_week_id: int) -> List[RecipeIngredient]:
        """Get all recipe ingredients for a planning week."""
        return db.query(RecipeIngredient).join(
            RecipeIngredient.recipe
        ).join(
            RecipeIngredient.recipe.has(
                Recipe.week_recipes.any(
                    WeekRecipe.planning_week_id == planning_week_id
                )
            )
        ).all()

    def _normalize_name(self, name: str) -> str:
        """Normalize ingredient/item names for matching."""
        if not name:
            return ""

        normalized = name.lower().strip()

        # Remove common words that don't affect matching
        stop_words = ['organic', 'fresh', 'whole', 'reduced', 'fat', 'free', 'natural']
        words = normalized.split()
        filtered_words = [word for word in words if word not in stop_words]

        return ' '.join(filtered_words)

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings."""
        # Use sequence matcher for basic similarity
        base_similarity = SequenceMatcher(None, str1, str2).ratio()

        # Boost score for exact word matches
        words1 = set(str1.split())
        words2 = set(str2.split())

        if words1 & words2:  # Has common words
            word_boost = len(words1 & words2) / max(len(words1), len(words2))
            base_similarity = min(1.0, base_similarity + word_boost * 0.2)

        return base_similarity

    def _create_match_suggestion(
        self,
        receipt_line: ReceiptLine,
        ingredient: RecipeIngredient,
        confidence: float
    ) -> Dict[str, Any]:
        """Create a match suggestion object."""

        # Calculate suggested consumption and price allocation
        suggested_qty = self._suggest_consumption_quantity(receipt_line, ingredient)
        suggested_price = self._suggest_price_allocation(receipt_line, suggested_qty)

        return {
            'receipt_line_id': receipt_line.id,
            'recipe_ingredient_id': ingredient.id,
            'confidence': confidence,
            'ingredient_name': ingredient.name,
            'receipt_item': receipt_line.normalized_name or receipt_line.raw_text,
            'suggested_qty_consumed': suggested_qty,
            'suggested_price': suggested_price,
            'unit': receipt_line.unit or ingredient.unit
        }

    def _suggest_consumption_quantity(
        self,
        receipt_line: ReceiptLine,
        ingredient: RecipeIngredient
    ) -> float:
        """Suggest how much of the purchased item was consumed for this recipe."""

        # Simple heuristic: assume full consumption if quantities are similar
        purchased_qty = receipt_line.qty or 1.0
        needed_qty = ingredient.qty

        # If units match and quantities are close, suggest needed quantity
        if receipt_line.unit == ingredient.unit:
            return min(purchased_qty, needed_qty)

        # Default to purchased quantity
        return purchased_qty

    def _suggest_price_allocation(
        self,
        receipt_line: ReceiptLine,
        qty_consumed: float
    ) -> float:
        """Suggest price allocation based on consumption."""

        total_price = receipt_line.line_price
        total_qty = receipt_line.qty or 1.0

        # Proportional allocation based on consumption
        return (qty_consumed / total_qty) * total_price