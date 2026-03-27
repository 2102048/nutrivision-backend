from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth_utils import get_current_user
from app import models
from app.schemas import SmartBMIRequest, SmartBMIResponse

router = APIRouter(prefix="/bmi", tags=["Smart BMI"])


@router.post("/smart", response_model=SmartBMIResponse)
def smart_bmi(
    data: SmartBMIRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # =============================
    # ✅ INPUT VALIDATION
    # =============================
    if data.height_cm <= 0:
        raise HTTPException(status_code=400, detail="Height must be greater than 0")

    if data.weight_kg <= 0:
        raise HTTPException(status_code=400, detail="Weight must be greater than 0")

    if data.age <= 0:
        raise HTTPException(status_code=400, detail="Age must be greater than 0")

    # =============================
    # BMI CALCULATION
    # =============================
    height_m = data.height_cm / 100
    bmi = round(data.weight_kg / (height_m ** 2), 2)

    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"

    # =============================
    # BMR CALCULATION (Mifflin-St Jeor)
    # =============================
    if data.gender.lower() == "male":
        bmr = 10 * data.weight_kg + 6.25 * data.height_cm - 5 * data.age + 5
    elif data.gender.lower() == "female":
        bmr = 10 * data.weight_kg + 6.25 * data.height_cm - 5 * data.age - 161
    else:
        raise HTTPException(status_code=400, detail="Gender must be 'male' or 'female'")

    activity_map = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725
    }

    if data.activity_level not in activity_map:
        raise HTTPException(status_code=400, detail="Invalid activity level")

    tdee = bmr * activity_map[data.activity_level]

    # =============================
    # 🔥 CALORIE RECOMMENDATION (SMART)
    # =============================
    goal_type = data.goal_type.lower()

    if goal_type == "gain":
        recommended_calories = tdee + 400
        recommendation = "Calorie surplus for healthy weight gain."
    elif goal_type == "lose":
        recommended_calories = tdee - 400
        recommendation = "Calorie deficit for fat loss."
    else:
        recommended_calories = tdee
        recommendation = "Maintain current weight."
        
    if category == "Underweight" and goal_type == "lose":
        recommendation = "You are underweight. Weight loss is not recommended."

    if category == "Obese" and goal_type == "gain":
        recommendation = "You are overweight. Weight gain is not recommended."

    # =============================
    # 🔥 MACRO SPLIT (SMART)
    # =============================
    if category == "Underweight":
        protein_ratio = 0.25
        carbs_ratio = 0.50
        fat_ratio = 0.25
    elif category in ["Overweight", "Obese"]:
        protein_ratio = 0.35
        carbs_ratio = 0.35
        fat_ratio = 0.30
    else:
        protein_ratio = 0.30
        carbs_ratio = 0.45
        fat_ratio = 0.25

    protein = round((recommended_calories * protein_ratio) / 4, 2)
    carbs = round((recommended_calories * carbs_ratio) / 4, 2)
    fat = round((recommended_calories * fat_ratio) / 9, 2)

    # =============================
    # 🧠 RECOMMENDATION TEXT
    # =============================
    if category == "Underweight":
        recommendation = "You are underweight. Increase calorie intake and focus on nutrient-rich foods."
    elif category == "Normal":
        recommendation = "You are in a healthy range. Maintain your current lifestyle."
    elif category == "Overweight":
        recommendation = "You are slightly overweight. A mild calorie deficit and activity will help."
    else:
        recommendation = "You are in the obese range. Follow a structured calorie deficit and exercise plan."

    # =============================
    # SAVE BMI RECORD
    # =============================
    bmi_record = models.BMIRecord(
        height_cm=data.height_cm,
        weight_kg=data.weight_kg,
        age=data.age,
        gender=data.gender,
        activity_level=data.activity_level,
        bmi=bmi,
        category=category,
        recommended_calories=recommended_calories,
        user_id=current_user.id
    )

    db.add(bmi_record)

    # =============================
    # 🔥 AUTO SYNC GOALS (FIXED)
    # =============================
    goal = db.query(models.UserGoal).filter(
        models.UserGoal.user_id == current_user.id
    ).first()

    if goal:
        goal.calorie_goal = recommended_calories
        goal.protein_goal = protein
        goal.carbs_goal = carbs
        goal.fat_goal = fat
        goal.goal_source = "bmi"   # ✅ IMPORTANT FIX
    else:
        new_goal = models.UserGoal(
            calorie_goal=recommended_calories,
            protein_goal=protein,
            carbs_goal=carbs,
            fat_goal=fat,
            user_id=current_user.id,
            goal_source="bmi"   # ✅ IMPORTANT FIX
        )
        db.add(new_goal)

    db.commit()

    # =============================
    # RESPONSE
    # =============================
    return {
        "bmi": bmi,
        "category": category,
        "bmr": round(bmr, 2),
        "tdee": round(tdee, 2),
        "recommended_calories": recommended_calories,
        "protein_grams": protein,
        "carbs_grams": carbs,
        "fat_grams": fat,
        "recommendation": recommendation
    }


# =============================
# BMI HISTORY
# =============================
@router.get("/history")
def bmi_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    records = db.query(models.BMIRecord).filter(
        models.BMIRecord.user_id == current_user.id
    ).order_by(models.BMIRecord.created_at.asc()).all()

    return records