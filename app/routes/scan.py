from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.image_classifier import classify_image
from app.services.nutrition_service import get_nutrition
from app.services.multi_food_parser import parse_multiple_foods
from typing import Union, List


router = APIRouter(prefix="/scan", tags=["Scan"])

# =========================
# 📸 SCAN FOOD IMAGE
# =========================
# This endpoint becomes: POST /scan/
@router.post("/")
async def scan_food(image: UploadFile = File(...)):
    if image.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(
            status_code=400,
            detail="Only JPEG and PNG images are allowed"
        )

    try:
        # 1️⃣ Classify image
        food_name = await classify_image(image)
        
        print(f"DEBUG: Image classified as {food_name}") # Log result

        # 2️⃣ Direct response
        return {
            "food_detected": food_name,
            "needs_confirmation": False
        }

    except Exception as e:
        print(f"SCAN ERROR: {e}")
        raise HTTPException(status_code=500, detail="Scan failed")


# =========================
# 🥗 GET NUTRITION DATA
# =========================
# This endpoint becomes: GET /scan/nutrition
@router.get("/nutrition")
def nutrition(
    food: str,
    quantity: str | None = None,
    unit: str | None = "piece"
):
    # Log the incoming request to debug 404s/mismatches
    print(f"DEBUG: Nutrition Request - Food: {food}, Qty: {quantity}, Unit: {unit}")

    # Clean quantity value
    if quantity in ["null", "", None]:
        quantity_val = 1.0
    else:
        try:
            quantity_val = float(quantity)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid quantity format")

    # Call Nutrition Service
    # We pass the unit as-is; service handles the math
    data = get_nutrition(food, quantity_val, unit)

    if not data:
        print(f"DEBUG: No data returned from Edamam for {food}")
        raise HTTPException(status_code=404, detail="Nutrition data not found")

    return {
        "food": food,
        "quantity": quantity_val,
        "unit": unit,
        "nutrition": data
    }
    
    # =========================
# 🍽 MULTI FOOD NUTRITION
# =========================
@router.get("/multi-nutrition")
def multi_nutrition(food_string: Union[str, List[str]]):

    # Ensure parser always gets a string
    if isinstance(food_string, list):
        food_string = ", ".join(food_string)

    foods = parse_multiple_foods(food_string)

    results = []
    total_calories = 0
    total_protein = 0
    total_fat = 0
    total_carbs = 0

    for item in foods:
        nutrition = get_nutrition(
            item["food"],
            item["quantity"],
            item["unit"]
        )

        if nutrition:
            results.append(nutrition)

            total_calories += nutrition["calories"]
            total_protein += nutrition["protein"]
            total_fat += nutrition["fat"]
            total_carbs += nutrition["carbs"]

    return {
        "foods": results,
        "totals": {
            "calories": round(total_calories, 1),
            "protein": round(total_protein, 1),
            "fat": round(total_fat, 1),
            "carbs": round(total_carbs, 1)
        }
    }