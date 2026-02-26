import json
import logging
import os
from typing import List, Dict, Set

logger = logging.getLogger(__name__)

CATEGORY_FILE = "categories.json"

DEFAULT_CATEGORIES = {
    "electronics": ["iphone", "samsung", "laptop", "tv", "camera"],
    "vehicles": ["toyota", "nissan", "subaru", "car", "bike"],
    "real_estate": ["apartment", "house", "land", "plot", "rent"],
    "jobs": ["driver", "cook", "manager", "developer", "sales"],
    "services": ["plumber", "electrician", "mechanic", "tutor", "cleaner"]
}

class CategoryManager:
    def __init__(self):
        self.categories: Dict[str, Set[str]] = {}
        self._load_categories()

    def _load_categories(self):
        if os.path.exists(CATEGORY_FILE):
            try:
                with open(CATEGORY_FILE, "r") as f:
                    data = json.load(f)
                    # Convert lists to sets for uniqueness
                    self.categories = {k: set(v) for k, v in data.items()}
                logger.info(f"Loaded {len(self.categories)} categories from {CATEGORY_FILE}")
            except Exception as e:
                logger.error(f"Failed to load categories: {e}")
                self.categories = {k: set(v) for k, v in DEFAULT_CATEGORIES.items()}
        else:
            self.categories = {k: set(v) for k, v in DEFAULT_CATEGORIES.items()}
            self._save_categories()

    def _save_categories(self):
        try:
            # Convert sets to lists for JSON
            data = {k: list(v) for k, v in self.categories.items()}
            with open(CATEGORY_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save categories: {e}")

    def get_keywords(self, category: str) -> List[str]:
        return list(self.categories.get(category, []))

    def add_keyword(self, category: str, keyword: str):
        if category not in self.categories:
            self.categories[category] = set()
        
        original_count = len(self.categories[category])
        self.categories[category].add(keyword.lower())
        
        if len(self.categories[category]) > original_count:
            logger.info(f"Added new keyword '{keyword}' to category '{category}'")
            self._save_categories()

    def expand_keywords_from_text(self, text: str, category: str):
        """
        Simple heuristic: if text contains high-value words not in list, add them.
        This is risky without NLP validation, so we'll be conservative.
        Only adds words that appear frequently or match certain patterns.
        """
        # Placeholder for more complex logic
        pass

CATEGORY_MANAGER = CategoryManager()
