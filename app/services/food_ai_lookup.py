import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def get_nutrition(food_data):

    food_name = food_data.get("name", "")
    quantity = food_data.get("quantity", 1)
    unit = food_data.get("unit", "piece")

    prompt = f"""
Estimate nutrition for the following food.

Food: {food_name}
Quantity: {quantity}
Unit: {unit}

Rules:
- If unit is piece, estimate for that number of pieces.
- If unit is plate assume 6 pieces.
- If unit is half plate assume 3 pieces.
- Return realistic nutrition values.

Return ONLY JSON:

{{
"food_name": "{food_name}",
"calories": number,
"protein": number,
"carbs": number,
"fat": number
}}
"""

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openai/gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
    )

    result = response.json()

    print("AI NUTRITION RESPONSE:", result)

    content = result["choices"][0]["message"]["content"]

    try:
        nutrition = json.loads(content)
    except:
        nutrition = {
            "food_name": food_name,
            "calories": 0,
            "protein": 0,
            "carbs": 0,
            "fat": 0
        }

    return nutrition