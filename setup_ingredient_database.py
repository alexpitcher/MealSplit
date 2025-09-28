#!/usr/bin/env python3
"""
Setup script to populate the ingredient database with real UK grocery ingredients.

This script creates 50+ common ingredients that you actually buy from UK supermarkets,
with proper units and variations to test the matching algorithm.
"""

import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from sqlalchemy.orm import Session
from app.core.database import engine, Base

# Import all models to ensure tables are created
from app.models.user import User
from app.models.household import Household, HouseholdUser
from app.models.planning import Recipe, RecipeIngredient, PlanningWeek, WeekRecipe, ShoppingItem, ShoppingItemLink
from app.models.receipt import Receipt, ReceiptLine, LineMatch
from app.models.settlement import Settlement, SplitwiseLink
from app.models.matching import UnitConversion, IngredientSynonym, UserMatchConfirmation


def create_sample_recipe(db: Session) -> Recipe:
    """Create a sample recipe to hold our ingredients."""
    recipe = Recipe(
        mealie_id="sample-recipe-001",
        title="Real UK Grocery Ingredients",
        base_servings=4,
        meta={"description": "Collection of real ingredients for testing matching"}
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


def setup_uk_ingredients(db: Session, recipe: Recipe):
    """Create comprehensive list of real UK grocery ingredients."""

    # Real UK grocery ingredients with variations you'd actually see
    ingredients_data = [
        # Fresh Produce
        ("bananas", 6, "count", ["banana", "banana bunch", "tesco bananas", "organic bananas"]),
        ("carrots", 1, "kg", ["carrot", "organic carrots", "baby carrots", "chantenay carrots"]),
        ("onions", 2, "kg", ["onion", "brown onions", "white onions", "spanish onions"]),
        ("potatoes", 2.5, "kg", ["potato", "maris piper", "king edward", "new potatoes"]),
        ("tomatoes", 500, "g", ["tomato", "cherry tomatoes", "plum tomatoes", "beef tomatoes"]),
        ("courgettes", 3, "count", ["courgette", "zucchini", "baby courgettes"]),
        ("aubergine", 1, "count", ["eggplant", "baby aubergines"]),
        ("red peppers", 3, "count", ["red pepper", "sweet red peppers", "romano peppers"]),
        ("broccoli", 1, "head", ["tenderstem broccoli", "purple sprouting broccoli"]),
        ("cauliflower", 1, "head", ["cauliflower florets"]),
        ("spinach", 200, "g", ["baby spinach", "leaf spinach", "washed spinach"]),
        ("rocket", 100, "g", ["arugula", "wild rocket", "baby rocket"]),
        ("lettuce", 1, "head", ["iceberg lettuce", "cos lettuce", "little gem"]),
        ("cucumber", 1, "count", ["baby cucumbers", "lebanese cucumber"]),
        ("spring onions", 1, "bunch", ["scallions", "green onions", "salad onions"]),
        ("garlic", 1, "bulb", ["garlic cloves", "peeled garlic"]),
        ("ginger", 100, "g", ["fresh ginger", "ginger root"]),
        ("lemons", 4, "count", ["lemon", "unwaxed lemons"]),
        ("limes", 6, "count", ["lime"]),
        ("apples", 6, "count", ["apple", "granny smith", "gala apples", "braeburn"]),
        ("pears", 4, "count", ["pear", "conference pears", "williams pears"]),

        # Meat & Fish
        ("chicken breast", 500, "g", ["chicken breasts", "skinless chicken breast"]),
        ("ground beef", 500, "g", ["beef mince", "lean beef mince", "british beef mince"]),
        ("pork chops", 4, "count", ["pork loin chops", "thick cut pork chops"]),
        ("bacon", 200, "g", ["back bacon", "streaky bacon", "smoked bacon"]),
        ("salmon fillet", 400, "g", ["salmon fillets", "scottish salmon", "organic salmon"]),
        ("cod fillet", 300, "g", ["cod fillets", "sustainable cod"]),
        ("prawns", 200, "g", ["king prawns", "cooked prawns", "raw prawns"]),

        # Dairy & Eggs
        ("milk", 1, "l", ["whole milk", "semi skimmed milk", "skimmed milk", "2 pint milk"]),
        ("eggs", 12, "count", ["free range eggs", "large eggs", "medium eggs", "6 pack eggs"]),
        ("butter", 250, "g", ["unsalted butter", "salted butter", "organic butter"]),
        ("cheddar cheese", 200, "g", ["mature cheddar", "mild cheddar", "extra mature cheddar"]),
        ("greek yogurt", 500, "g", ["natural yogurt", "low fat yogurt", "total greek yogurt"]),
        ("cream", 300, "ml", ["double cream", "single cream", "whipping cream"]),

        # Pantry Staples
        ("bread", 1, "loaf", ["white bread", "brown bread", "wholemeal bread", "seeded bread"]),
        ("pasta", 500, "g", ["spaghetti", "penne", "fusilli", "whole wheat pasta"]),
        ("rice", 1, "kg", ["basmati rice", "long grain rice", "brown rice", "jasmine rice"]),
        ("flour", 1.5, "kg", ["plain flour", "self raising flour", "strong white flour"]),
        ("sugar", 1, "kg", ["caster sugar", "granulated sugar", "brown sugar"]),
        ("olive oil", 500, "ml", ["extra virgin olive oil", "light olive oil"]),
        ("vegetable oil", 1, "l", ["sunflower oil", "rapeseed oil"]),
        ("salt", 1, "pack", ["sea salt", "table salt", "rock salt"]),
        ("black pepper", 1, "pack", ["ground black pepper", "whole peppercorns"]),

        # Canned/Packaged Goods
        ("tinned tomatoes", 400, "g", ["chopped tomatoes", "whole plum tomatoes", "passata"]),
        ("baked beans", 400, "g", ["heinz baked beans", "reduced sugar beans"]),
        ("kidney beans", 400, "g", ["red kidney beans", "dried kidney beans"]),
        ("chickpeas", 400, "g", ["dried chickpeas", "cooked chickpeas"]),
        ("coconut milk", 400, "ml", ["full fat coconut milk", "light coconut milk"]),
        ("stock cubes", 1, "pack", ["chicken stock", "vegetable stock", "beef stock"]),
        ("worcestershire sauce", 1, "bottle", ["lea & perrins"]),
        ("soy sauce", 150, "ml", ["dark soy sauce", "light soy sauce", "reduced salt"]),

        # Frozen
        ("frozen peas", 500, "g", ["garden peas", "petit pois", "mushy peas"]),
        ("frozen sweetcorn", 500, "g", ["corn kernels"]),
        ("frozen prawns", 500, "g", ["cooked frozen prawns", "raw frozen prawns"]),

        # Herbs & Spices
        ("basil", 1, "pack", ["fresh basil", "dried basil", "basil leaves"]),
        ("parsley", 1, "pack", ["flat leaf parsley", "curly parsley", "fresh parsley"]),
        ("coriander", 1, "pack", ["fresh coriander", "cilantro"]),
        ("cumin", 1, "jar", ["ground cumin", "cumin seeds"]),
        ("paprika", 1, "jar", ["smoked paprika", "sweet paprika"]),
        ("oregano", 1, "jar", ["dried oregano", "fresh oregano"]),
    ]

    print(f"Creating {len(ingredients_data)} real UK ingredients...")

    for name, qty, unit, synonyms in ingredients_data:
        # Create the main ingredient
        ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            name=name,
            qty=qty,
            unit=unit,
            tags={"category": "real_ingredient", "synonyms": synonyms}
        )
        db.add(ingredient)
        db.commit()
        db.refresh(ingredient)

        # Add synonyms for better matching
        for synonym in synonyms:
            if synonym.lower() != name.lower():
                synonym_entry = IngredientSynonym(
                    ingredient_id=ingredient.id,
                    synonym=synonym,
                    normalized_synonym=synonym.lower().strip(),
                    source="system",
                    confidence=0.9
                )
                db.add(synonym_entry)

    db.commit()
    print(f"✅ Created {len(ingredients_data)} ingredients with synonyms")


def setup_uk_unit_conversions(db: Session):
    """Set up UK-specific unit conversions."""

    conversions_data = [
        # Weight conversions (to grams)
        ("kg", "g", 1000.0, "weight"),
        ("kilogram", "g", 1000.0, "weight"),
        ("lb", "g", 453.592, "weight"),
        ("lbs", "g", 453.592, "weight"),
        ("pound", "g", 453.592, "weight"),
        ("oz", "g", 28.3495, "weight"),
        ("ounce", "g", 28.3495, "weight"),
        ("stone", "g", 6350.29, "weight"),

        # Volume conversions (to milliliters)
        ("l", "ml", 1000.0, "volume"),
        ("litre", "ml", 1000.0, "volume"),
        ("pint", "ml", 568.261, "volume"),  # UK pint
        ("pt", "ml", 568.261, "volume"),
        ("fl oz", "ml", 28.4131, "volume"),  # UK fluid ounce
        ("floz", "ml", 28.4131, "volume"),
        ("gallon", "ml", 4546.09, "volume"),  # UK gallon
        ("cup", "ml", 284.131, "volume"),    # UK cup

        # Count units
        ("pack", "unit", 1.0, "count"),
        ("packet", "unit", 1.0, "count"),
        ("box", "unit", 1.0, "count"),
        ("tin", "unit", 1.0, "count"),
        ("can", "unit", 1.0, "count"),
        ("bottle", "unit", 1.0, "count"),
        ("jar", "unit", 1.0, "count"),
        ("bag", "unit", 1.0, "count"),
        ("loaf", "unit", 1.0, "count"),
        ("head", "unit", 1.0, "count"),
        ("bulb", "unit", 1.0, "count"),
        ("bunch", "unit", 1.0, "count"),
        ("count", "unit", 1.0, "count"),
    ]

    print("Setting up UK unit conversions...")

    for from_unit, to_unit, multiplier, unit_type in conversions_data:
        conversion = UnitConversion(
            from_unit=from_unit,
            to_unit=to_unit,
            multiplier=multiplier,
            unit_type=unit_type
        )
        db.add(conversion)

    db.commit()
    print(f"✅ Created {len(conversions_data)} unit conversions")


def main():
    """Main setup function."""
    print("🛒 Setting up Real UK Grocery Ingredient Database")
    print("=" * 60)

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create database session
    from app.core.database import SessionLocal
    db = SessionLocal()

    try:
        # Check if we already have ingredients
        existing_ingredients = db.query(RecipeIngredient).count()
        if existing_ingredients > 0:
            print(f"⚠️  Found {existing_ingredients} existing ingredients.")
            response = input("Do you want to clear and recreate? (y/N): ")
            if response.lower() != 'y':
                print("Setup cancelled.")
                return

            # Clear existing data
            db.query(IngredientSynonym).delete()
            db.query(UnitConversion).delete()
            db.query(RecipeIngredient).delete()
            db.query(Recipe).delete()
            db.commit()
            print("🗑️  Cleared existing data")

        # Create sample recipe to hold ingredients
        recipe = create_sample_recipe(db)
        print(f"📝 Created sample recipe: {recipe.title}")

        # Setup ingredients and conversions
        setup_uk_ingredients(db, recipe)
        setup_uk_unit_conversions(db)

        print("\n🎉 Database setup complete!")
        print("\nNext steps:")
        print("1. Test the matching algorithm: python3 test_matching.py")
        print("2. Upload a real receipt: use the API /api/v1/receipts/")
        print("3. Check matches: /api/v1/receipts/{id}/matches/pending")

    except Exception as e:
        print(f"❌ Error during setup: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()