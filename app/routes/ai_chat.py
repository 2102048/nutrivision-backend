from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.ai_service import extract_food_info
from app.services.ai_nutrition_estimator import estimate_nutrition

router = APIRouter(prefix="/ai", tags=["AI Chat"])


class ChatRequest(BaseModel):
    message: str


@router.post("/food")
def ai_food_chat(req: ChatRequest):

    try:

        # STEP 1 — Extract foods
        data = extract_food_info(req.message)

        # If AI returns wrapped structure
        if isinstance(data, dict) and "foodItems" in data:
            foods = data["foodItems"]
        else:
            foods = data
        if not foods:
            raise HTTPException(status_code=400, detail="Food not detected")

        results = []
        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0

        for food in foods:

    
            # If AI returns string instead of dict
            if isinstance(food, str):
                food_name = food
                quantity = 1
                unit = "serving"
            else:
                food_name = food.get("name")
                quantity = float(food.get("quantity", 1))
                unit = food.get("unit", "serving")            

            nutrition = estimate_nutrition(
                food_name,
                quantity,
                unit
            )

            calories = float(nutrition.get("calories", 0)) * quantity
            protein = float(nutrition.get("protein", 0)) * quantity
            carbs = float(nutrition.get("carbs", 0)) * quantity
            fat = float(nutrition.get("fat", 0)) * quantity

            results.append({
                "food_name": food_name,
                "quantity": quantity,
                "unit": unit,
                "calories": round(calories,2),
                "protein": round(protein,2),
                "carbs": round(carbs,2),
                "fat": round(fat,2)
            })

            total_calories += calories
            total_protein += protein
            total_carbs += carbs
            total_fat += fat

        return {
            "foods": results,
            "totals": {
                "calories": round(total_calories,2),
                "protein": round(total_protein,2),
                "carbs": round(total_carbs,2),
                "fat": round(total_fat,2)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))