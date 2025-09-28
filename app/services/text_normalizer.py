import re
from typing import List, Set


class TextNormalizer:
    """Advanced text normalization for grocery receipt items."""

    def __init__(self):
        # UK grocery store brands to remove
        self.uk_brands = {
            # Major supermarket brands
            "tesco", "tesco finest", "tesco value", "tesco everyday value",
            "sainsbury's", "sainsburys", "taste the difference", "basics",
            "asda", "asda extra special", "asda smart price", "george",
            "morrisons", "m savers", "the best", "eat smart",
            "waitrose", "waitrose essential", "waitrose 1", "duchy organic",
            "marks & spencer", "m&s", "marks and spencer",
            "aldi", "specially selected", "simply", "nature's pick",
            "lidl", "deluxe", "organic", "bio organic",
            "co-op", "coop", "co operative", "truly irresistible",
            "iceland", "iceland luxury",

            # Generic brands and descriptors
            "own brand", "store brand", "house brand", "supermarket",
            "fresh", "freshly", "farm fresh", "garden fresh",
            "premium", "finest", "best", "select", "choice", "quality",
            "extra special", "luxury", "gourmet", "artisan", "traditional",
            "classic", "original", "authentic", "genuine", "real",
            "natural", "pure", "wholesome", "healthy", "nutritious",
            "organic", "bio", "eco", "free range", "outdoor bred",
            "grass fed", "corn fed", "wild", "sustainable",
            "fair trade", "fairtrade", "ethical", "responsible",
            "local", "british", "uk", "scottish", "welsh", "irish",
            "homemade", "home style", "farmhouse", "country", "village",
            "value", "economy", "basic", "essentials", "smart price",
            "everyday", "standard", "regular", "normal",
        }

        # Marketing words that add no nutritional value
        self.marketing_words = {
            "new", "improved", "extra", "super", "mega", "jumbo", "giant",
            "family", "sharing", "party", "celebration", "festive",
            "limited edition", "special", "seasonal", "summer", "winter",
            "crispy", "crunchy", "smooth", "creamy", "rich", "indulgent",
            "light", "lite", "reduced", "low fat", "diet", "zero",
            "vitamin", "protein", "fiber", "fibre", "enriched", "fortified",
            "handpicked", "selected", "carefully", "lovingly", "perfectly",
            "delicious", "tasty", "flavourful", "mouthwatering", "irresistible",
        }

        # Common pluralization patterns
        self.plural_patterns = [
            (r"ies$", "y"),     # berries -> berry
            (r"ves$", "f"),     # leaves -> leaf
            (r"ses$", "s"),     # glasses -> glass
            (r"ches$", "ch"),   # peaches -> peach
            (r"shes$", "sh"),   # dishes -> dish
            (r"xes$", "x"),     # boxes -> box
            (r"oes$", "o"),     # tomatoes -> tomato
            (r"s$", ""),        # apples -> apple
        ]

        # Weight/volume indicators to normalize
        self.measurement_patterns = [
            r"\b\d+(?:\.\d+)?\s*(?:kg|g|lb|lbs|oz|ounces?)\b",
            r"\b\d+(?:\.\d+)?\s*(?:l|ml|pint|pints|litre|litres?)\b",
            r"\b\d+(?:\.\d+)?\s*(?:pack|packs|x|count|ct)\b",
            r"\b\d+\s*for\s*£?\d+(?:\.\d+)?\b",  # "3 for £5"
            r"\b£?\d+(?:\.\d+)?\s*each\b",
            r"\bper\s+\w+\b",
        ]

    def normalize(self, text: str) -> str:
        """Full normalization pipeline for grocery item text."""
        if not text:
            return ""

        # Step 1: Basic cleaning
        normalized = self._basic_clean(text)

        # Step 2: Remove brands and marketing words
        normalized = self._remove_brands(normalized)
        normalized = self._remove_marketing_words(normalized)

        # Step 3: Remove measurements and pricing
        normalized = self._remove_measurements(normalized)

        # Step 4: Handle plurals
        normalized = self._normalize_plurals(normalized)

        # Step 5: Final cleanup
        normalized = self._final_cleanup(normalized)

        return normalized.strip()

    def _basic_clean(self, text: str) -> str:
        """Basic text cleaning and standardization."""
        # Convert to lowercase
        text = text.lower()

        # Fix common OCR artifacts
        text = text.replace("'", "'")  # Fix apostrophes
        text = text.replace(""", '"').replace(""", '"')  # Fix quotes
        text = text.replace("–", "-").replace("—", "-")  # Fix dashes

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove common punctuation that doesn't add meaning
        text = re.sub(r'[.,;:!?(){}[\]"]', ' ', text)

        return text.strip()

    def _remove_brands(self, text: str) -> str:
        """Remove UK grocery store brands and descriptors."""
        words = text.split()
        filtered_words = []

        for word in words:
            # Check if word (or combination) is a brand
            if word not in self.uk_brands:
                # Check for multi-word brands
                found_brand = False
                for brand in self.uk_brands:
                    if len(brand.split()) > 1 and brand in text:
                        text = text.replace(brand, " ")
                        found_brand = True
                        break

                if not found_brand:
                    filtered_words.append(word)

        return " ".join(filtered_words)

    def _remove_marketing_words(self, text: str) -> str:
        """Remove marketing buzzwords."""
        words = text.split()
        filtered_words = [word for word in words if word not in self.marketing_words]
        return " ".join(filtered_words)

    def _remove_measurements(self, text: str) -> str:
        """Remove weight, volume, and pricing information."""
        for pattern in self.measurement_patterns:
            text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

        # Remove standalone numbers that likely represent weights/quantities
        text = re.sub(r'\b\d+(?:\.\d+)?\b', " ", text)

        return text

    def _normalize_plurals(self, text: str) -> str:
        """Convert plurals to singular forms."""
        words = text.split()
        normalized_words = []

        for word in words:
            singular = self._singularize(word)
            normalized_words.append(singular)

        return " ".join(normalized_words)

    def _singularize(self, word: str) -> str:
        """Convert a single word from plural to singular."""
        if len(word) <= 3:  # Skip very short words
            return word

        # Try each pluralization pattern
        for pattern, replacement in self.plural_patterns:
            if re.search(pattern, word):
                return re.sub(pattern, replacement, word)

        return word

    def _final_cleanup(self, text: str) -> str:
        """Final cleanup pass."""
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)

        # Remove single characters (likely artifacts)
        words = text.split()
        words = [word for word in words if len(word) > 1]

        # Remove common prepositions and articles that don't help matching
        stop_words = {"the", "a", "an", "of", "in", "on", "at", "to", "for", "with", "and", "or"}
        words = [word for word in words if word not in stop_words]

        return " ".join(words)

    def get_synonyms(self, text: str) -> List[str]:
        """Generate common synonyms for ingredient matching."""
        synonyms = [text]

        # Common UK/US variations
        uk_us_variations = {
            "courgette": ["zucchini"],
            "aubergine": ["eggplant"],
            "mange tout": ["snow peas", "snap peas"],
            "rocket": ["arugula"],
            "coriander": ["cilantro"],
            "spring onion": ["scallion", "green onion"],
            "swede": ["rutabaga"],
            "turnip": ["neep"],
        }

        # Check for variations
        for uk_term, us_terms in uk_us_variations.items():
            if uk_term in text:
                synonyms.extend([text.replace(uk_term, us_term) for us_term in us_terms])
            for us_term in us_terms:
                if us_term in text:
                    synonyms.append(text.replace(us_term, uk_term))

        return list(set(synonyms))  # Remove duplicates