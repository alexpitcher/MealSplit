from typing import Dict, Any, List, Optional, Tuple
import logging
from sqlalchemy.orm import Session
from rapidfuzz import fuzz, process
from dataclasses import dataclass

from app.models.planning import RecipeIngredient, PlanningWeek, WeekRecipe
from app.models.receipt import ReceiptLine, LineMatch
from app.models.matching import UserMatchConfirmation, IngredientSynonym
from app.services.text_normalizer import TextNormalizer
from app.services.unit_converter import UnitConverter
from app.services.gemini_service import GeminiService, cosine_similarity
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of ingredient matching."""
    recipe_ingredient_id: int
    ingredient_name: str
    confidence: float
    suggested_qty_consumed: float
    suggested_price: float
    match_reason: str
    unit_compatible: bool


class AdvancedMatchingService:
    """Advanced service for matching receipt items to recipe ingredients."""

    def __init__(self):
        self.normalizer = TextNormalizer()
        self.unit_converter = UnitConverter()
        self.gemini = GeminiService()

        # Matching thresholds (Gemini mandatory)
        # We bias towards embeddings; auto-match above 0.85, review between 0.6-0.85
        self.exact_threshold = 0.90
        self.high_confidence_threshold = 0.85
        self.medium_confidence_threshold = 0.60
        self.min_threshold = 0.50

    def find_matches_for_receipt_line(self, db: Session, receipt_line: ReceiptLine, week_id: int) -> List[Dict[str, Any]]:
        """Find potential ingredient matches for a receipt line using multi-stage pipeline."""

        if not self.gemini.is_enabled():
            raise RuntimeError("Gemini AI is required for matching but is not configured")

        logger.info(f"Finding matches for receipt line: {receipt_line.raw_text}")

        # Get all available ingredients
        ingredients = db.query(RecipeIngredient).all()
        if not ingredients:
            logger.warning("No ingredients found in database")
            return []

        # Stage 1: Normalize the receipt text
        normalized_text = self.normalizer.normalize(receipt_line.raw_text)
        logger.debug(f"Normalized text: '{receipt_line.raw_text}' -> '{normalized_text}'")

        # Stage 2: Gemini normalization boost (mandatory)
        gem_norm = self.gemini.normalize_text(normalized_text)
        normalized_candidate = gem_norm or normalized_text

        # Stage 3: Multi-stage matching + embedding boost
        matches = self._multi_stage_matching(normalized_candidate, ingredients, receipt_line)
        try:
            # Compute an embedding for receipt text and for all ingredient names
            ing_names = [self.normalizer.normalize(ing.name) for ing in ingredients]
            embeds = self.gemini.embed_texts([normalized_candidate] + ing_names)
            if embeds and len(embeds) == 1 + len(ingredients):
                qvec = embeds[0]
                ing_vecs = embeds[1:]
                # Blend cosine similarity into confidence
                alpha = 0.7  # weight for embeddings
                by_id = {ing.id: vec for ing, vec in zip(ingredients, ing_vecs)}
                for m in matches:
                    vec = by_id.get(m.recipe_ingredient_id)
                    if vec:
                        emb_sim = cosine_similarity(qvec, vec)
                        m.confidence = min(1.0, alpha * emb_sim + (1 - alpha) * m.confidence)
        except Exception:
            pass

        # Stage 3: Context-aware filtering (boost ingredients in current week)
        matches = self._apply_context_boost(matches, week_id, db)

        # Stage 4: Learn from previous confirmations
        matches = self._apply_learning_boost(matches, normalized_text, db)

        # Convert to API format
        results = []
        for match in matches[:5]:  # Top 5 matches
            results.append({
                "recipe_ingredient_id": match.recipe_ingredient_id,
                "confidence": match.confidence,
                "suggested_qty_consumed": match.suggested_qty_consumed,
                "suggested_price": match.suggested_price,
                "match_reason": match.match_reason,
                "ingredient_name": match.ingredient_name,
                "unit_compatible": match.unit_compatible
            })

        logger.info(f"Found {len(results)} matches for '{receipt_line.raw_text}'")
        return results

    def auto_match_high_confidence(self, db: Session, receipt_line: ReceiptLine, planning_week_id: int) -> Optional[LineMatch]:
        """Automatically create matches for high-confidence suggestions."""
        matches = self.find_matches_for_receipt_line(db, receipt_line, planning_week_id)

        if not matches:
            return None

        best_match = matches[0]
        if best_match['confidence'] >= self.exact_threshold:
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

    def _multi_stage_matching(self, normalized_text: str, ingredients: List[RecipeIngredient], receipt_line: ReceiptLine) -> List[MatchResult]:
        """Multi-stage matching pipeline."""
        matches = []

        for ingredient in ingredients:
            # Stage 1: Exact match after normalization
            normalized_ingredient = self.normalizer.normalize(ingredient.name)

            if normalized_text == normalized_ingredient:
                match = self._create_match_result(
                    ingredient, 1.0, receipt_line, "Exact normalized match"
                )
                matches.append(match)
                continue

            # Stage 2: Fuzzy text similarity
            fuzzy_score = fuzz.ratio(normalized_text, normalized_ingredient) / 100.0

            if fuzzy_score >= self.min_threshold:
                reason = self._get_fuzzy_reason(fuzzy_score)
                match = self._create_match_result(
                    ingredient, fuzzy_score, receipt_line, reason
                )
                matches.append(match)
                continue

            # Stage 3: Partial matching (word-level)
            partial_score = self._partial_word_match(normalized_text, normalized_ingredient)

            if partial_score >= self.min_threshold:
                match = self._create_match_result(
                    ingredient, partial_score, receipt_line, "Partial word match"
                )
                matches.append(match)
                continue

            # Stage 4: Synonym matching
            synonym_score = self._synonym_match(normalized_text, normalized_ingredient)

            if synonym_score >= self.min_threshold:
                match = self._create_match_result(
                    ingredient, synonym_score, receipt_line, "Synonym match"
                )
                matches.append(match)

        # Sort by confidence
        matches.sort(key=lambda x: x.confidence, reverse=True)
        return matches

    def _create_match_result(self, ingredient: RecipeIngredient, confidence: float, receipt_line: ReceiptLine, reason: str) -> MatchResult:
        """Create a match result with unit compatibility check."""

        # Check unit compatibility
        receipt_qty, receipt_unit = self.unit_converter.parse_quantity_unit(receipt_line.raw_text)
        unit_compatible = self.unit_converter.are_units_compatible(receipt_unit, ingredient.unit)

        # Adjust confidence based on unit compatibility
        adjusted_confidence = confidence
        if not unit_compatible:
            adjusted_confidence *= 0.8  # Reduce confidence for incompatible units

        # Calculate suggested consumption (default to purchased quantity)
        suggested_qty = receipt_line.qty or receipt_qty or 1.0

        return MatchResult(
            recipe_ingredient_id=ingredient.id,
            ingredient_name=ingredient.name,
            confidence=adjusted_confidence,
            suggested_qty_consumed=suggested_qty,
            suggested_price=receipt_line.line_price or 0.0,
            match_reason=reason,
            unit_compatible=unit_compatible
        )

    def _get_fuzzy_reason(self, score: float) -> str:
        """Get human-readable reason for fuzzy match."""
        if score >= self.exact_threshold:
            return "Near exact match"
        elif score >= self.high_confidence_threshold:
            return "High confidence fuzzy match"
        elif score >= self.medium_confidence_threshold:
            return "Medium confidence fuzzy match"
        else:
            return "Low confidence fuzzy match"

    def _partial_word_match(self, text1: str, text2: str) -> float:
        """Check for partial word matches."""
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    def _synonym_match(self, text1: str, text2: str) -> float:
        """Check for synonym matches using the normalizer."""
        synonyms1 = self.normalizer.get_synonyms(text1)
        synonyms2 = self.normalizer.get_synonyms(text2)

        best_score = 0.0
        for syn1 in synonyms1:
            for syn2 in synonyms2:
                score = fuzz.ratio(syn1, syn2) / 100.0
                best_score = max(best_score, score)

        return best_score

    def _apply_context_boost(self, matches: List[MatchResult], week_id: int, db: Session) -> List[MatchResult]:
        """Boost confidence for ingredients in the current planning week."""

        # Get ingredients that are planned for this week
        week = db.query(PlanningWeek).filter(PlanningWeek.id == week_id).first()
        if not week:
            return matches

        # Get recipe ingredients for this week
        week_ingredient_ids = set()
        week_recipes = db.query(WeekRecipe).filter(WeekRecipe.planning_week_id == week_id).all()

        for week_recipe in week_recipes:
            recipe_ingredients = db.query(RecipeIngredient).filter(
                RecipeIngredient.recipe_id == week_recipe.recipe_id
            ).all()
            week_ingredient_ids.update(ing.id for ing in recipe_ingredients)

        # Boost matches for ingredients in this week
        for match in matches:
            if match.recipe_ingredient_id in week_ingredient_ids:
                match.confidence = min(1.0, match.confidence * 1.2)  # 20% boost
                match.match_reason += " (planned this week)"

        return matches

    def _apply_learning_boost(self, matches: List[MatchResult], normalized_text: str, db: Session) -> List[MatchResult]:
        """Boost confidence based on previous user confirmations."""

        # Get previous confirmations for similar text
        confirmations = db.query(UserMatchConfirmation).filter(
            UserMatchConfirmation.normalized_text == normalized_text,
            UserMatchConfirmation.was_correct == True
        ).all()

        confirmed_ingredient_ids = {conf.ingredient_id for conf in confirmations}

        # Boost matches for previously confirmed ingredients
        for match in matches:
            if match.recipe_ingredient_id in confirmed_ingredient_ids:
                match.confidence = min(1.0, match.confidence * 1.15)  # 15% boost
                match.match_reason += " (previously confirmed)"

        return matches

    def confirm_match(self, db: Session, user_id: int, receipt_line_id: int, ingredient_id: int, was_correct: bool) -> None:
        """Store a user confirmation for learning."""

        receipt_line = db.query(ReceiptLine).filter(ReceiptLine.id == receipt_line_id).first()
        if not receipt_line:
            return

        normalized_text = self.normalizer.normalize(receipt_line.raw_text)

        confirmation = UserMatchConfirmation(
            user_id=user_id,
            receipt_text=receipt_line.raw_text,
            normalized_text=normalized_text,
            ingredient_id=ingredient_id,
            confidence_score=1.0 if was_correct else 0.0,
            was_correct=was_correct
        )

        db.add(confirmation)
        db.commit()

        logger.info(f"Stored match confirmation: {receipt_line.raw_text} -> ingredient {ingredient_id} ({'correct' if was_correct else 'incorrect'})")
