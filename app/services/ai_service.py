import requests
import os
import json
import re

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

URL = "https://openrouter.ai/api/v1/chat/completions"


def extract_food_info(user_text: str):

    prompt = f"""
You are a food extraction AI.

Extract food items from the sentence.

Sentence:
"{user_text}"

Return ONLY valid JSON.

Always return an ARRAY.

Format:

[
 {{
  "name": "food name",
  "quantity": number,
  "unit": "piece | plate | bowl | slice | glass | cup | serving"
 }}
]

Examples:

Input: I ate 2 samosas
Output:
[
 {{
  "name": "samosa",
  "quantity": 2,
  "unit": "piece"
 }}
]

Input: I ate chicken momo
Output:
[
 {{
  "name": "chicken momo",
  "quantity": 1,
  "unit": "serving"
 }}
]

Rules:
- If quantity missing → quantity = 1
- If unit missing → unit = serving
- Return ONLY JSON
- No explanation
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(URL, headers=headers, json=data)

    result = response.json()

    print("AI RESPONSE:", result)

    if "choices" not in result:
        raise Exception(f"AI API Error: {result}")

    text = result["choices"][0]["message"]["content"]

    # 🔧 CLEAN RESPONSE
    text = text.replace("```json", "").replace("```", "")
    text = re.sub(r"//.*", "", text)

    try:
        data = json.loads(text)

        # If AI returns single object → convert to list
        if isinstance(data, dict):
            return [data]

        return data

    except Exception as e:

        print("JSON PARSE ERROR:", e)
        print("RAW:", text)

        return [{
            "name": user_text,
            "quantity": 1,
            "unit": "serving"
        }]