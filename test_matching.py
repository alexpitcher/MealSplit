#!/usr/bin/env python3
"""
Test script for the advanced matching algorithm.

This script tests the matching service with real UK grocery receipt items
to verify it can match against the ingredient database.
"""

import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal

# Import all models to ensure proper relationships
from app.models.user import User
from app.models.household import Household, HouseholdUser
from app.models.planning import RecipeIngredient, PlanningWeek, WeekRecipe, Recipe, ShoppingItem, ShoppingItemLink
from app.models.receipt import ReceiptLine, Receipt, LineMatch
from app.models.settlement import Settlement, SplitwiseLink
from app.models.matching import UnitConversion, IngredientSynonym, UserMatchConfirmation

from app.services.advanced_matching_service import AdvancedMatchingService
from app.services.text_normalizer import TextNormalizer
from app.services.unit_converter import UnitConverter


def test_text_normalization():
    """Test the text normalization pipeline."""
    print("🧹 Testing Text Normalization")
    print("-" * 40)

    normalizer = TextNormalizer()

    test_cases = [
        "Tesco Finest British Beef Mince 500g",
        "Sainsbury's Organic Free Range Eggs 12 Pack",
        "ASDA Extra Special Mature Cheddar Cheese 200g",
        "Morrisons The Best Smoked Scottish Salmon 200g",
        "Waitrose Duchy Organic Bananas 6 Pack",
        "Co-op Irresistible Italian Extra Virgin Olive Oil 500ml",
        "Aldi Specially Selected Artisan Sourdough Bread",
        "Lidl Deluxe Premium Greek Style Natural Yogurt 500g"
    ]

    for item in test_cases:
        normalized = normalizer.normalize(item)
        print(f"  '{item}'")
        print(f"  -> '{normalized}'")
        print()


def test_unit_conversion():
    """Test the unit conversion system."""
    print("⚖️  Testing Unit Conversion")
    print("-" * 40)

    converter = UnitConverter()

    test_cases = [
        (2.5, "kg"),
        (500, "g"),
        (1, "pint"),
        (568, "ml"),
        (1, "lb"),
        (6, "pack"),
        (12, "count"),
        (1.5, "l"),
    ]

    for qty, unit in test_cases:
        normalized_qty, normalized_unit = converter.normalize_unit(qty, unit)
        print(f"  {qty} {unit} -> {normalized_qty} {normalized_unit}")


def test_quantity_parsing():
    """Test quantity and unit parsing from receipt text."""
    print("📊 Testing Quantity Parsing")
    print("-" * 40)

    converter = UnitConverter()

    test_cases = [
        "Bananas 6 pack £1.50",
        "Milk 2 pint £2.20",
        "Beef Mince 500g £4.99",
        "Chicken Breast 1.2kg £7.50",
        "Baked Beans 400g tin £0.80",
        "Olive Oil 500ml bottle £3.99",
        "Eggs 12 count £2.50",
        "Bread 800g loaf £1.20",
    ]

    for text in test_cases:
        qty, unit = converter.parse_quantity_unit(text)
        print(f"  '{text}'")
        print(f"  -> {qty} {unit}")
        print()


def test_matching_algorithm(db: Session):
    """Test the matching algorithm with real receipt items."""
    print("🎯 Testing Matching Algorithm")
    print("-" * 40)

    matcher = AdvancedMatchingService()

    # Get sample ingredients count
    ingredient_count = db.query(RecipeIngredient).count()
    print(f"Available ingredients: {ingredient_count}")

    if ingredient_count == 0:
        print("❌ No ingredients found! Run setup_ingredient_database.py first")
        return

    # Test receipt items (real examples from UK receipts)
    test_receipt_items = [
        "Tesco Bananas 6 pack £1.50",
        "Sainsbury's Beef Mince 500g £4.99",
        "ASDA Milk 2 pint £2.20",
        "Morrisons Free Range Eggs 12 £2.50",
        "Waitrose Organic Carrots 1kg £1.80",
        "Co-op Mature Cheddar 200g £2.99",
        "Aldi Chicken Breast 500g £3.99",
        "Lidl Pasta Fusilli 500g £0.89",
        "Tesco Finest Olive Oil 500ml £4.50",
        "ASDA Smart Price Bread £0.36",
        "Sainsbury's Taste the Difference Salmon 400g £6.00",
        "Morrisons Savers Baked Beans 400g £0.35",
    ]

    for i, item_text in enumerate(test_receipt_items, 1):
        print(f"\n{i:2d}. Testing: '{item_text}'")

        # Create a mock receipt line
        receipt_line = ReceiptLine(
            id=i,
            receipt_id=1,
            raw_text=item_text,
            normalized_name=None,
            qty=1.0,
            unit="unit",
            line_price=2.50
        )

        # Find matches
        matches = matcher.find_matches_for_receipt_line(db, receipt_line, week_id=1)

        if matches:
            print(f"    Found {len(matches)} matches:")
            for j, match in enumerate(matches[:3], 1):  # Top 3
                print(f"      {j}. {match['ingredient_name']} "
                      f"(confidence: {match['confidence']:.1%}, "
                      f"reason: {match['match_reason']})")
        else:
            print("    ❌ No matches found")


def test_specific_matches(db: Session):
    """Test specific challenging matches."""
    print("\n🔍 Testing Challenging Matches")
    print("-" * 40)

    matcher = AdvancedMatchingService()

    challenging_cases = [
        ("Tesco Finest British Beef Mince 500g", "ground beef"),
        ("Sainsbury's Free Range Large Eggs 12", "eggs"),
        ("ASDA Extra Special Mature Cheddar", "cheddar cheese"),
        ("Waitrose Duchy Organic Bananas", "bananas"),
        ("Co-op Irresistible Courgettes 3 pack", "courgettes"),
        ("Morrisons The Best Smoked Salmon", "salmon fillet"),
    ]

    for receipt_text, expected_ingredient in challenging_cases:
        print(f"\nTesting: '{receipt_text}'")
        print(f"Expected: '{expected_ingredient}'")

        receipt_line = ReceiptLine(
            id=1,
            receipt_id=1,
            raw_text=receipt_text,
            normalized_name=None,
            qty=1.0,
            unit="unit",
            line_price=3.99
        )

        matches = matcher.find_matches_for_receipt_line(db, receipt_line, week_id=1)

        if matches:
            best_match = matches[0]
            success = expected_ingredient.lower() in best_match['ingredient_name'].lower()
            status = "✅" if success else "❌"
            print(f"  {status} Best match: {best_match['ingredient_name']} "
                  f"({best_match['confidence']:.1%})")
        else:
            print("  ❌ No matches found")


def main():
    """Main test function."""
    print("🧪 Testing MealSplit Advanced Matching Algorithm")
    print("=" * 60)

    # Test text processing components
    test_text_normalization()
    print()

    test_unit_conversion()
    print()

    test_quantity_parsing()
    print()

    # Test matching with database
    db = SessionLocal()
    try:
        test_matching_algorithm(db)
        test_specific_matches(db)

        print("\n🎉 Matching tests complete!")
        print("\nTo improve results:")
        print("1. Add more ingredient synonyms")
        print("2. Adjust confidence thresholds")
        print("3. Test with your actual receipts")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()