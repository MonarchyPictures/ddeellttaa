
try:
    from sentence_transformers import SentenceTransformer, util
    import torch
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

class LeadDeduper:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = None
        if HAS_TRANSFORMERS:
            try:
                self.model = SentenceTransformer(model_name)
            except:
                self.model = None

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Semantic similarity between two strings."""
        if not text1 or not text2:
            return 0.0
            
        if self.model:
            embeddings = self.model.encode([text1, text2])
            cos_sim = util.cos_sim(embeddings[0], embeddings[1])
            return float(cos_sim.item())
        
        # Fallback: Simple set-based Jaccard similarity
        s1 = set(text1.lower().split())
        s2 = set(text2.lower().split())
        if not s1 or not s2: return 0.0
        return len(s1 & s2) / len(s1 | s2)

    def is_duplicate(self, new_text: str, existing_texts: list, threshold=0.85) -> bool:
        """Checks if a new lead is a duplicate of existing ones."""
        if not new_text or not existing_texts:
            return False
            
        if self.model and len(existing_texts) > 0:
            new_emb = self.model.encode(new_text)
            ext_emb = self.model.encode(existing_texts)
            scores = util.cos_sim(new_emb, ext_emb)
            return float(torch.max(scores).item()) >= threshold
            
        # Fallback loop
        for old_text in existing_texts:
            if self.calculate_similarity(new_text, old_text) >= threshold:
                return True
        return False
