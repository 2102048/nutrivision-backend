from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List

from app import models, schemas
from app.database import get_db
from app.auth_utils import get_current_user

router = APIRouter(prefix="/meals", tags=["Meals"])


# ➕ Add Meal
@router.post("/", response_model=schemas.MealResponse)
def add_meal(
    meal: schemas.MealCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    new_meal = models.Meal(
        name=meal.name,
        category=meal.category,
        calories=meal.calories,
        protein=meal.protein,
        carbs=meal.carbs,
        fat=meal.fat,
        user_id=current_user.id
    )

    db.add(new_meal)
    db.commit()
    db.refresh(new_meal)


    return new_meal


# 📋 Get Meals
@router.get("/", response_model=List[schemas.MealResponse])
def get_meals(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    meals = (
        db.query(models.Meal)
        .filter(
            or_(
                models.Meal.user_id == current_user.id,
                models.Meal.user_id == None  # legacy meals
            )
        )
        .order_by(models.Meal.created_at.desc())
        .all()
    )

    return meals


# ❌ Delete Meal
@router.delete("/{meal_id}")
def delete_meal(
    meal_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    meal = db.query(models.Meal).filter(
        models.Meal.id == meal_id,
        models.Meal.user_id == current_user.id
    ).first()

    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found"
        )

    db.delete(meal)
    db.commit()

    return {"message": "Meal deleted successfully"}