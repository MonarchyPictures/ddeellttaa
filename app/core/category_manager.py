import json
import os
import logging
from typing import List, Dict, Set
from collections import Counter
from app.core.category_config import CategoryConfig

logger = logging.getLogger(__name__)

class CategoryManager:
    """
    Manages dynamic category configurations.
    Allows runtime expansion of keywords and persistence.
    """
    
    PERSISTENCE_FILE = "category_updates.json"
    
    def __init__(self):
        self.categories = CategoryConfig.CATEGORIES.copy()
        self._load_updates()
        
    def _load_updates(self):
        """Load dynamic updates from file."""
        if os.path.exists(self.PERSISTENCE_FILE):
            try:
                with open(self.PERSISTENCE_FILE, "r") as f:
                    updates = json.load(f)
                    for cat, data in updates.items():
                        if cat in self.categories:
                            # Merge keywords
                            current_keywords = set(self.categories[cat]["keywords"])
                            new_keywords = set(data.get("keywords", []))
                            self.categories[cat]["keywords"] = list(current_keywords.union(new_keywords))
                            
                            # Merge search terms
                            current_terms = set(self.categories[cat]["search_terms"])
                            new_terms = set(data.get("search_terms", []))
                            self.categories[cat]["search_terms"] = list(current_terms.union(new_terms))
                            
                    logger.info(f"Loaded category updates from {self.PERSISTENCE_FILE}")
            except Exception as e:
                logger.error(f"Failed to load category updates: {e}")

    def _save_updates(self):
        """Save dynamic updates to file."""
        updates = {}
        for cat, data in self.categories.items():
            # diff against original config to save space? 
            # For simplicity, we just save the current state of mutable fields
            updates[cat] = {
                "keywords": data["keywords"],
                "search_terms": data["search_terms"]
            }
            
        try:
            with open(self.PERSISTENCE_FILE, "w") as f:
                json.dump(updates, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save category updates: {e}")

    def get_keywords(self, category: str) -> List[str]:
        return self.categories.get(category, {}).get("keywords", [])

    def add_keyword(self, category: str, keyword: str):
        if category not in self.categories:
            return
            
        keyword = keyword.lower().strip()
        if keyword and keyword not in self.categories[category]["keywords"]:
            self.categories[category]["keywords"].append(keyword)
            self._save_updates()
            logger.info(f"Added new keyword '{keyword}' to category '{category}'")

    def expand_keywords_from_text(self, category: str, text: str):
        """
        Analyzes text to find potential new keywords.
        This is a simplified version. A real version would use NLP to extract Noun Phrases.
        """
        if category not in self.categories:
            return

        # Simple heuristic: If we find a word that appears frequently in high-quality leads
        # but isn't in our list, we might want to add it.
        # For now, we'll just log potential candidates.
        
        # TODO: Implement TF-IDF or similar to find unique significant words
        pass

CATEGORY_MANAGER = CategoryManager()
