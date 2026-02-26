
import unittest
from app.intelligence.query_expander import SmartQueryExpander, get_expanded_queries
from app.services.market_classifier import calculate_kenyan_intent_score, is_valid_buyer

class TestQueryExpansionAndScoring(unittest.TestCase):
    
    def test_query_expansion_matrix(self):
        """Test if 'buy house' generates Intent x Location x Property x Budget matrix"""
        seed = "buy house"
        # Now passing location context to trigger default locations
        expanded = SmartQueryExpander.generate_combinations(seed, location_context="Kenya")
        
        print(f"\nExpanded '{seed}' into {len(expanded)} queries.")
        
        # Check for presence of key combinations
        self.assertTrue(any("kilimani" in q for q in expanded), "Should contain Kilimani")
        self.assertTrue(any("house" in q for q in expanded), "Should contain House")
        self.assertTrue(any("want to buy" in q for q in expanded), "Should contain Intent 'want to buy'")
        self.assertTrue(any("budget" in q for q in expanded), "Should contain Budget")
        
        # Check limit
        self.assertLessEqual(len(expanded), 50, "Should be capped at 50")

    def test_social_patterns(self):
        """Test if social patterns are generated"""
        seed = "apartment kilimani"
        expanded = SmartQueryExpander.generate_combinations(seed, location_context="Kenya")
        
        social_hits = [q for q in expanded if "anyone selling" in q or "who has" in q]
        self.assertTrue(len(social_hits) > 0, "Should generate social queries")
        print(f"Social queries sample: {social_hits[:2]}")

    def test_query_intent_scoring(self):
        """Test if query context adds points to the score"""
        text = "I am looking for a house in Nairobi." # Basic buyer phrase (+30) + Location (+15) = 45. Below 50.
        
        # Without query context
        score_base, _ = calculate_kenyan_intent_score(text)
        # 30 (buyer) + 15 (loc) = 45. 
        # Wait, "I am looking" -> "looking" is in FIRST_PERSON_PRONOUNS, "looking for" is in BUYER_INTENT.
        # score = 30 + 15 = 45.
        
        # With "urgent" query context (+20)
        score_urgent, details = calculate_kenyan_intent_score(text, query_context="urgent house needed")
        print(f"\nScore Base: {score_base}")
        print(f"Score Urgent: {score_urgent} -> {details}")
        
        self.assertTrue(score_urgent > score_base, "Query context should increase score")
        self.assertEqual(score_urgent, score_base + 20, "Should add exactly 20 for urgency")
        
        # With "cash" query context (+30)
        score_cash, details_cash = calculate_kenyan_intent_score(text, query_context="cash buyer")
        self.assertEqual(score_cash, score_base + 30, "Should add exactly 30 for cash")

    def test_seller_blocklist(self):
        """Test strict negative filtering"""
        text = "We are listed by agent and have property for sale."
        is_valid = is_valid_buyer(text)
        self.assertFalse(is_valid, "Should reject 'listed by agent'")
        
        text2 = "Contact broker for details."
        is_valid2 = is_valid_buyer(text2)
        self.assertFalse(is_valid2, "Should reject 'contact broker'")

if __name__ == '__main__':
    unittest.main()
