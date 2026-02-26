import json
from scraper import LeadScraper
from intent import IntentEngine
from utils import LeadUtils

def main():
    scraper = LeadScraper()
    intent_engine = IntentEngine()
    utils = LeadUtils()

    print("--- Starting Savage Lead Gen Engine ---")

    # Target categories and platforms
    categories = ["tires", "bulk sugar", "furniture", "tanks"]
    platforms = ["reddit", "tiktok", "facebook", "twitter", "google"]
    all_leads = []

    for platform in platforms:
        for category in categories:
            try:
                raw_results = scraper.scrape_platform(platform, category)
                
                for raw in raw_results:
                    score = intent_engine.calculate_intent_score(raw['text'])
                    if score > 0.4:
                        lead = utils.format_lead(
                            raw.get('platform', platform), 
                            raw['link'], 
                            raw['text'], 
                            raw.get('category', category), 
                            raw.get('user', 'Unknown')
                        )
                        lead['intent_score'] = score
                        lead['personalized_message'] = utils.generate_message(lead)
                        lead['contact_status'] = "not_contacted"
                        all_leads.append(lead)
            except Exception as e:
                print(f"Error scraping {platform} for {category}: {e}")

    print(f"Extracted {len(all_leads)} fresh leads.")
    print(json.dumps(all_leads, indent=2))

if __name__ == "__main__":
    main()
