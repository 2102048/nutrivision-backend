from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth_utils import get_current_user
from app import models, schemas

from app.auth_utils import verify_password, hash_password

router = APIRouter(
    prefix="/profile",
    tags=["Profile"]
)


# =========================
# GET PROFILE
# =========================

@router.get("/", response_model=schemas.UserResponse)
def get_profile(
    current_user: models.User = Depends(get_current_user)
):
    return current_user


# =========================
# UPDATE NAME
# =========================

@router.put("/update-name", response_model=schemas.UserResponse)
def update_name(
    data: schemas.UpdateName,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    current_user.name = data.name

    db.commit()
    db.refresh(current_user)

    return current_user


# =========================
# GET LATEST HEALTH DATA
# =========================

@router.get("/health", response_model=schemas.HealthResponse)
def get_health(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    record = (
        db.query(models.BMIRecord)
        .filter(models.BMIRecord.user_id == current_user.id)
        .order_by(models.BMIRecord.created_at.desc())
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=404,
            detail="No health data found. Please add your health information."
        )

    return record


# =========================
# UPDATE HEALTH INFO
# =========================

@router.post("/update-health", response_model=schemas.HealthResponse)
def update_health(
    data: schemas.UpdateHealth,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    # -------------------------
    # BMI Calculation
    # -------------------------
    height_m = data.height_cm / 100
    bmi = data.weight_kg / (height_m ** 2)

    # -------------------------
    # BMI Category
    # -------------------------
    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"

    # -------------------------
    # BMR Calculation
    # -------------------------
    if data.gender.lower() == "male":
        bmr = 10 * data.weight_kg + 6.25 * data.height_cm - 5 * data.age + 5
    else:
        bmr = 10 * data.weight_kg + 6.25 * data.height_cm - 5 * data.age - 161

    # -------------------------
    # Activity multiplier
    # -------------------------
    activity_map = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9
    }

    multiplier = activity_map.get(data.activity_level, 1.2)

    # -------------------------
    # TDEE (Recommended Calories)
    # -------------------------
    recommended_calories = bmr * multiplier

    # -------------------------
    # Save record
    # -------------------------
    record = models.BMIRecord(
        user_id=current_user.id,
        age=data.age,
        gender=data.gender,
        height_cm=data.height_cm,
        weight_kg=data.weight_kg,
        activity_level=data.activity_level,
        bmi=bmi,
        category=category,
        recommended_calories=recommended_calories
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record


# =========================
# UPDATE EMAIL
# =========================

@router.put("/update-email", response_model=schemas.UserResponse)
def update_email(
    data: schemas.UpdateEmail,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    # check if email already exists
    existing = db.query(models.User).filter(models.User.email == data.email).first()

    if existing:
        raise HTTPException(status_code=400, detail="Email already in use")

    current_user.email = data.email
    db.commit()
    db.refresh(current_user)

    return current_user


# =========================
# CHANGE PASSWORD
# =========================

@router.put("/change-password")
def change_password(
    data: schemas.ChangePassword,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    # verify current password
    if not verify_password(data.current_password, current_user.password):
        raise HTTPException(status_code=400, detail="Current password incorrect")

    # hash new password
    current_user.password = hash_password(data.new_password)

    db.commit()

    return {"message": "Password updated successfully"}