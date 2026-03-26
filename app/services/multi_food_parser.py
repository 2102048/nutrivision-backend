import re

def parse_multiple_foods(food_input):
    """
    Accepts:
    "1 toast,1 mango,1 apple"
    OR
    ["1 toast","1 mango","1 apple"]
    """

    foods = []

    # If FastAPI sends list convert to string
    if isinstance(food_input, list):
        parts = food_input
    else:
        parts = food_input.split(",")

    for part in parts:
        part = part.strip()

        match = re.match(r"(\d+\.?\d*)\s+(.*)", part)

        if match:
            quantity = float(match.group(1))
            food = match.group(2)
        else:
            quantity = 1.0
            food = part

        foods.append({
            "food": food,
            "quantity": quantity,
            "unit": "piece"
        })

    return foods