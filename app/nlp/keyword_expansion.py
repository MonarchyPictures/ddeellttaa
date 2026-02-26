# spacy disabled due to Pydantic V1 incompatibility on Python 3.12+
spacy = None
# try:
#     import spacy
# except ImportError:
#     spacy = None

try:
    from sentence_transformers import SentenceTransformer, util
    import torch
except ImportError:
    SentenceTransformer = None
    util = None
    torch = None

from ..core.category_config import CategoryConfig

class KeywordExpander:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = None
        if SentenceTransformer:
            try:
                self.model = SentenceTransformer(model_name)
            except Exception:
                self.model = None
            
        # Load active categories from central config
        self.industry_dicts = {
            k: v["keywords"] 
            for k, v in CategoryConfig.CATEGORIES.items() 
            if v["is_active"]
        }

    def expand_keywords(self, seed_keyword, top_k=5):
        """Expand a seed keyword using semantic similarity."""
        if not self.model:
            return [seed_keyword]
            
        # This is a simplified version; in production, you'd search a large corpus
        # or use a pre-computed synonym database like WordNet.
        # For now, we'll check against our industry dictionaries.
        expanded = [seed_keyword]
        for industry, words in self.industry_dicts.items():
            if seed_keyword.lower() in words:
                expanded.extend([w for w in words if w != seed_keyword.lower()])
                break
                
        return list(set(expanded))[:top_k+1]

    def identify_emerging_terms(self, post_texts):
        """Analyze a batch of posts to find frequent new terms (ML-based)."""
        # Placeholder for future TF-IDF/NER implementation
        # currently returns empty list to avoid mock data pollution
        return []
