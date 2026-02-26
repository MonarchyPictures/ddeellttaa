
class OutreachEngine:
    def generate_message(self, lead):
        """
        📌 BUYER-FIRST OUTREACH GENERATOR
        Personalized to intent, budget, and location.
        Example: “Hi John, saw you’re looking for a Toyota Axio around 1.1M in Nairobi. I have one available — can we talk?”
        """
        # Support both dict and object (SQLAlchemy model)
        is_dict = isinstance(lead, dict)
        
        # Extract fields for personalization
        name = (lead.get('name') or lead.get('buyer_name')) if is_dict else getattr(lead, 'buyer_name', None)
        if not name or name == "Verified Market Signal":
            name = "there"
            
        product = (lead.get('product') or lead.get('product_category')) if is_dict else getattr(lead, 'product_category', 'this item')
        budget = lead.get('budget') if is_dict else getattr(lead, 'budget', None)
        location = (lead.get('location') or lead.get('location_raw')) if is_dict else getattr(lead, 'location_raw', 'Nairobi')
        intent = (lead.get('intent') or lead.get('buyer_intent_quote')) if is_dict else getattr(lead, 'buyer_request_snippet', '')
        
        # 📝 ENHANCED MESSAGE LOGIC (User Requested)
        buyer_match_score = lead.get('buyer_match_score', 0) if is_dict else getattr(lead, 'buyer_match_score', 0)
        
        if buyer_match_score >= 0.85:
            return (
                f"Hi {name}, I saw you’re actively looking for a {product}. "
                "I have a clean option in Nairobi and can share details now. "
                "Are you ready to proceed?"
            )

        return (
            f"Hi {name}, I came across your interest in a {product}. "
            "Is it still something you’re looking to buy?"
        )

def generate_message(lead):
    return OutreachEngine().generate_message(lead)
