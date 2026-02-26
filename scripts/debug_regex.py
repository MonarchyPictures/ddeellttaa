
import re

text = "I am looking for a 50,000L tank in Nairobi ASAP. Budget is around 400k. Contact me on 0712345678 or email john@example.com. Need it delivered to Westlands."
pattern = "looking for"
match = re.search(rf"{pattern}\s+(?:a|an|the)?\s*([\w\s,]+?)(?:\s+in\b|\s+at\b|\s+by\b|\s+with\b|\s+for\b|\s+asap\b|\.|\,|$)", text, re.IGNORECASE)
if match:
    print(f"Matched: '{match.group(1).strip()}'")
else:
    print("No match")

text2 = "Searching for a clean Toyota Camry 2005 model."
pattern2 = "searching for"
match2 = re.search(rf"{pattern2}\s+(?:a|an|the)?\s*([\w\s,]+?)(?:\s+in\b|\s+at\b|\s+by\b|\s+with\b|\s+for\b|\s+asap\b|\.|\,|$)", text2, re.IGNORECASE)
if match2:
    print(f"Matched 2: '{match2.group(1).strip()}'")
