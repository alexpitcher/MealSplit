#!/usr/bin/env python3
"""
Test the full MealSplit pipeline: OCR → Receipt Lines → Matching → Results
"""

import sys
import asyncio
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal

# Import all models
from app.models.user import User
from app.models.household import Household, HouseholdUser
from app.models.planning import Recipe, RecipeIngredient, PlanningWeek, WeekRecipe, ShoppingItem, ShoppingItemLink
from app.models.receipt import Receipt, ReceiptLine, LineMatch
from app.models.settlement import Settlement, SplitwiseLink
from app.models.matching import UnitConversion, IngredientSynonym, UserMatchConfirmation

from app.services.ocr_service import OCRService
from app.services.advanced_matching_service import AdvancedMatchingService


async def test_full_pipeline():
    """Test the complete pipeline from receipt to matches."""
    print("🧪 Testing Complete MealSplit Pipeline")
    print("=" * 50)

    # Initialize services
    ocr_service = OCRService()
    matching_service = AdvancedMatchingService()
    db = SessionLocal()

    try:
        # Step 1: Process a receipt with OCR
        print("📸 Step 1: Processing receipt with OCR...")
        receipt_file = "test_real_receipt.txt"

        ocr_result = await ocr_service.process_receipt_image(receipt_file)
        print(f"   ✅ OCR processed {len(ocr_result['items'])} items")
        print(f"   📝 Store: {ocr_result['store_name']}")
        print(f"   💰 Total: {ocr_result['currency']}{ocr_result['total_amount']:.2f}")

        # Step 2: Create receipt lines (simulating API behavior)
        print("\n🗃️  Step 2: Creating receipt lines...")
        receipt_lines = []

        for i, item in enumerate(ocr_result['items'], 1):
            line = ReceiptLine(
                id=i,
                receipt_id=1,  # Mock receipt ID
                raw_text=item['name'],
                normalized_name=None,
                qty=item.get('quantity', 1.0),
                unit=item.get('unit', 'unit'),
                line_price=item.get('total_price', 0.0)
            )
            receipt_lines.append(line)

        print(f"   ✅ Created {len(receipt_lines)} receipt lines")

        # Step 3: Test matching for each line
        print("\n🎯 Step 3: Finding ingredient matches...")

        total_matches = 0
        high_confidence_matches = 0
        auto_matches = 0

        for line in receipt_lines:
            print(f"\n   📝 Processing: '{line.raw_text}'")

            # Find matches
            matches = matching_service.find_matches_for_receipt_line(db, line, week_id=1)

            if matches:
                total_matches += 1
                best_match = matches[0]
                confidence = best_match['confidence']

                print(f"      🎯 Best match: {best_match['ingredient_name']}")
                print(f"      📊 Confidence: {confidence:.1%}")
                print(f"      🔍 Reason: {best_match['match_reason']}")

                if confidence >= 0.8:
                    high_confidence_matches += 1

                if confidence >= 0.95:
                    auto_matches += 1
                    print("      ✅ Would auto-match!")

                # Show top 3 matches
                if len(matches) > 1:
                    print("      📋 Other suggestions:")
                    for match in matches[1:3]:
                        print(f"         - {match['ingredient_name']} ({match['confidence']:.1%})")
            else:
                print("      ❌ No matches found")

        # Step 4: Statistics
        print(f"\n📊 Step 4: Pipeline Results")
        print("-" * 30)
        print(f"   Total items processed: {len(receipt_lines)}")
        print(f"   Items with matches: {total_matches}")
        print(f"   High confidence (80%+): {high_confidence_matches}")
        print(f"   Auto-match eligible (95%+): {auto_matches}")

        match_rate = (total_matches / len(receipt_lines)) * 100 if receipt_lines else 0
        auto_rate = (auto_matches / len(receipt_lines)) * 100 if receipt_lines else 0

        print(f"   Overall match rate: {match_rate:.1f}%")
        print(f"   Auto-match rate: {auto_rate:.1f}%")

        # Step 5: Assessment
        print(f"\n🎯 Assessment:")
        if match_rate >= 70:
            print("   ✅ EXCELLENT: Meeting 70%+ match rate target!")
        elif match_rate >= 50:
            print("   ✨ GOOD: Above 50% match rate")
        else:
            print("   🔧 NEEDS WORK: Below 50% match rate")

        if auto_rate >= 30:
            print("   ✅ GREAT: High auto-match rate for efficiency")
        else:
            print("   📝 MANUAL REVIEW: Most items need manual confirmation")

        print(f"\n🎉 Pipeline test complete!")
        print("   Ready for real grocery receipts! 🛒")

    except Exception as e:
        print(f"❌ Error during pipeline test: {e}")
        raise
    finally:
        db.close()


async def main():
    """Main test function."""
    await test_full_pipeline()


if __name__ == "__main__":
    asyncio.run(main())