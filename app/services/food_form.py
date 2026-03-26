RAW_KEYWORDS = ["raw", "fresh", "whole"]
PROCESSED_KEYWORDS = ["dried", "powder", "chips", "flour"]

def detect_food_form(food_name: str):
    name = food_name.lower()

    for word in PROCESSED_KEYWORDS:
        if word in name:
            return {
                "form": word,
                "confidence": "high",
                "needs_confirmation": False
            }

    # MobileNet almost never says "raw banana"
    # So default assumption is RAW but ask user
    return {
        "form": "raw",
        "confidence": "low",
        "needs_confirmation": True,
        "options": ["raw", "dried", "powder", "chips"]
    }
