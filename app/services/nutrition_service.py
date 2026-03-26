import os
import requests
import logging
from dotenv import load_dotenv

# Initialize logging for large-scale monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NutritionService")

load_dotenv()

EDAMAM_APP_ID = os.getenv("EDAMAM_APP_ID")
EDAMAM_APP_KEY = os.getenv("EDAMAM_APP_KEY")
BASE_URL = "https://api.edamam.com/api/food-database/v2/parser"

import re

def clean_query(food_query: str) -> str:
    # 1. Replace underscores and dashes with spaces
    query = food_query.replace("_", " ").replace("-", " ")
    
    # 2. Remove any character that isn't a letter, number, or space
    query = re.sub(r'[^a-zA-Z0-9\s]', '', query)
    
    # 3. Clean up extra whitespace and lowercase it
    return " ".join(query.split()).lower()

def get_nutrition(food_query: str, quantity: float = 1.0, requested_unit: str = "piece"):
    if not EDAMAM_APP_ID or not EDAMAM_APP_KEY:
        logger.error("Missing Edamam credentials in environment variables.")
        return None

    # Step 1: Clean the query
    original_query = food_query
    search_query = clean_query(food_query)

    try:
        # --------------------------------
        # 1️⃣ API Request Logic
        # --------------------------------
        params = {
            "app_id": EDAMAM_APP_ID,
            "app_key": EDAMAM_APP_KEY,
            "ingr": search_query,
            "nutrition-type": "logging"
        }

        response = requests.get(BASE_URL, params=params, timeout=10)

        if response.status_code != 200:
            logger.error(f"Edamam API returned error {response.status_code}: {response.text}")
            return None

        data = response.json()

        # --------------------------------
        # 2️⃣ Fallback Logic (The 'Smart' Search)
        # --------------------------------
        # If no results and the query has multiple words, try the last word (the base food)
        if not data.get("hints") or len(data["hints"]) == 0:
            words = search_query.split()
            if len(words) > 1:
                logger.info(f"No results for '{search_query}'. Trying fallback: '{words[-1]}'")
                return get_nutrition(words[-1], quantity, requested_unit)
            
            logger.warning(f"No nutrition data found for: {search_query}")
            return None

        # --------------------------------
        # 3️⃣ Data Extraction
        # --------------------------------
        first_match = data["hints"][0]
        food_item = first_match["food"]
        nutrients = food_item.get("nutrients", {})
        measures = first_match.get("measures", [])

        # --------------------------------
        # 4️⃣ Determine Weight Per Unit
        # --------------------------------
        unit_lower = requested_unit.lower()
        gram_per_unit = None

        if unit_lower in ["g", "gram", "grams"]:
            gram_per_unit = 1
        elif unit_lower in ["kg", "kilogram"]:
            gram_per_unit = 1000
        else:
            # Match piece/serving/unit against Edamam's measure list
            for measure in measures:
                label = measure.get("label", "").lower()
                if any(word in label for word in ["piece", "whole", "serving", "each", "unit", "cup"]):
                    gram_per_unit = measure.get("weight")
                    break

        # Standard fallback to 100g if no unit matched
        if gram_per_unit is None:
            logger.info(f"Unit '{requested_unit}' not found for {search_query}. Falling back to 100g standard.")
            gram_per_unit = 100

        # --------------------------------
        # 5️⃣ Final Calculations
        # --------------------------------
        total_grams = quantity * gram_per_unit
        # Edamam nutrients are provided per 100g
        multiplier = total_grams / 100

        result = {
            "food_name": food_item.get("label"),
            "display_name": search_query.title(),
            "quantity": quantity,
            "unit": requested_unit,
            "calculated_weight_grams": round(total_grams, 1),
            "calories": round(nutrients.get("ENERC_KCAL", 0) * multiplier, 1),
            "protein": round(nutrients.get("PROCNT", 0) * multiplier, 1),
            "fat": round(nutrients.get("FAT", 0) * multiplier, 1),
            "carbs": round(nutrients.get("CHOCDF", 0) * multiplier, 1),
        }

        logger.info(f"Successfully calculated nutrition for {search_query}")
        return result

    except requests.exceptions.Timeout:
        logger.error("Edamam API request timed out.")
        return None
    except Exception as e:
        logger.error(f"Internal Nutrition Service Error: {str(e)}")
        return None
    
    
    # ==========================================
# MULTI FOOD SUPPORT (Industry Level Feature)
# ==========================================

def get_multiple_food_nutrition(food_list):
    """
    Accepts a list of food names and returns nutrition separately
    """
    results = []

    for food in food_list:
        nutrition = get_nutrition(food)

        if nutrition:
            results.append(nutrition)

    return results
    