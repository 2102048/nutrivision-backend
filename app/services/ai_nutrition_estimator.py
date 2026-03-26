import requests
import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def estimate_nutrition(food_name, quantity, unit):

    prompt = f"""
You are a professional nutritionist.

Estimate realistic nutrition values.

Food: {food_name}
Quantity: {quantity}
Unit: {unit}

Rules:
- If unit is piece → calculate per piece
- If unit is plate → typical restaurant serving
- If unit is bowl → medium bowl
- If unit is slice → normal slice
- If quantity is 0.5 → half portion

Return ONLY valid JSON.

Example format:
{{
"name": "{food_name}",
"calories": number,
"protein": number,
"carbs": number,
"fat": number
}}

Do NOT include comments.
Do NOT include explanations.
Only return JSON.
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

    # 🔧 Clean AI output
    content = content.replace("```json", "").replace("```", "")
    content = re.sub(r"//.*", "", content)  # remove comments

    try:
        return json.loads(content)

    except Exception as e:
        print("JSON PARSE ERROR:", e)
        print("RAW AI RESPONSE:", content)

        return {
            "name": food_name,
            "calories": 0,
            "protein": 0,
            "carbs": 0,
            "fat": 0
        }