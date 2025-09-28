import re
from typing import Dict, Optional, Tuple
from decimal import Decimal


class UnitConverter:
    """Handle unit conversions for UK grocery measurements."""

    def __init__(self):
        # Standard unit conversions to base units
        self.conversions = {
            # Weight conversions (to grams)
            "weight": {
                "kg": 1000.0,
                "kilogram": 1000.0,
                "kilograms": 1000.0,
                "g": 1.0,
                "gram": 1.0,
                "grams": 1.0,
                "lb": 453.592,
                "lbs": 453.592,
                "pound": 453.592,
                "pounds": 453.592,
                "oz": 28.3495,
                "ounce": 28.3495,
                "ounces": 28.3495,
                "stone": 6350.29,
                "stones": 6350.29,
            },

            # Volume conversions (to milliliters)
            "volume": {
                "l": 1000.0,
                "litre": 1000.0,
                "litres": 1000.0,
                "liter": 1000.0,
                "liters": 1000.0,
                "ml": 1.0,
                "millilitre": 1.0,
                "millilitres": 1.0,
                "milliliter": 1.0,
                "milliliters": 1.0,
                "pint": 568.261,  # UK pint
                "pints": 568.261,
                "pt": 568.261,
                "fl oz": 28.4131,  # UK fluid ounce
                "floz": 28.4131,
                "fluid ounce": 28.4131,
                "fluid ounces": 28.4131,
                "gallon": 4546.09,  # UK gallon
                "gallons": 4546.09,
                "gal": 4546.09,
                "cup": 284.131,  # UK cup (half pint)
                "cups": 284.131,
            },

            # Count/discrete units
            "count": {
                "pack": 1.0,
                "packs": 1.0,
                "packet": 1.0,
                "packets": 1.0,
                "box": 1.0,
                "boxes": 1.0,
                "tin": 1.0,
                "tins": 1.0,
                "can": 1.0,
                "cans": 1.0,
                "bottle": 1.0,
                "bottles": 1.0,
                "jar": 1.0,
                "jars": 1.0,
                "bag": 1.0,
                "bags": 1.0,
                "piece": 1.0,
                "pieces": 1.0,
                "item": 1.0,
                "items": 1.0,
                "unit": 1.0,
                "units": 1.0,
                "each": 1.0,
            }
        }

        # Pack size patterns for extracting quantities
        self.pack_patterns = [
            r"(\d+(?:\.\d+)?)\s*pack",
            r"(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s*count",
            r"(\d+(?:\.\d+)?)\s*ct",
        ]

    def normalize_unit(self, quantity: float, unit: str) -> Tuple[float, str]:
        """Normalize a quantity and unit to base units."""
        if not unit:
            return quantity, "unit"

        unit_lower = unit.lower().strip()

        # Try to find the unit type and convert
        for unit_type, conversions in self.conversions.items():
            if unit_lower in conversions:
                base_unit = self._get_base_unit(unit_type)
                multiplier = conversions[unit_lower]
                normalized_quantity = quantity * multiplier
                return normalized_quantity, base_unit

        # If no conversion found, return as-is
        return quantity, unit_lower

    def _get_base_unit(self, unit_type: str) -> str:
        """Get the base unit for a unit type."""
        base_units = {
            "weight": "g",
            "volume": "ml",
            "count": "unit"
        }
        return base_units.get(unit_type, "unit")

    def are_units_compatible(self, unit1: str, unit2: str) -> bool:
        """Check if two units are compatible (same type)."""
        type1 = self._get_unit_type(unit1)
        type2 = self._get_unit_type(unit2)
        return type1 == type2 and type1 is not None

    def _get_unit_type(self, unit: str) -> Optional[str]:
        """Get the type of a unit (weight, volume, count)."""
        if not unit:
            return None

        unit_lower = unit.lower().strip()

        for unit_type, conversions in self.conversions.items():
            if unit_lower in conversions:
                return unit_type

        return None

    def extract_pack_size(self, text: str) -> Tuple[Optional[float], Optional[str]]:
        """Extract pack size information from text."""
        text_lower = text.lower()

        # Look for pack size patterns
        for pattern in self.pack_patterns:
            match = re.search(pattern, text_lower)
            if match:
                if len(match.groups()) == 1:
                    # Simple pack: "6 pack"
                    return float(match.group(1)), "pack"
                else:
                    # Multiplied pack: "3 x 500g"
                    count = float(match.group(1))
                    size = float(match.group(2))
                    return count * size, "unit"

        return None, None

    def parse_quantity_unit(self, text: str) -> Tuple[float, str]:
        """Parse quantity and unit from text with advanced patterns."""
        text = text.strip()

        # Pattern for quantity + unit (e.g., "2.5kg", "500 ml", "1 pint")
        quantity_patterns = [
            r"(\d+(?:\.\d+)?)\s*(kg|g|lb|lbs|oz|l|ml|pint|pints|litre|litres)",
            r"(\d+(?:\.\d+)?)\s*(pack|packs|bottle|bottles|tin|tins|can|cans)",
            r"(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*(g|ml|oz)",
        ]

        for pattern in quantity_patterns:
            match = re.search(pattern, text.lower())
            if match:
                if len(match.groups()) == 2:
                    qty = float(match.group(1))
                    unit = match.group(2)
                    return qty, unit
                elif len(match.groups()) == 3:
                    # Handle "3 x 500g" format
                    count = float(match.group(1))
                    size = float(match.group(2))
                    unit = match.group(3)
                    return count * size, unit

        # Default to 1 unit if no quantity found
        return 1.0, "unit"