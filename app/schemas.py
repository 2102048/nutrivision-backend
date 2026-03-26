from pydantic import BaseModel, EmailStr
from datetime import datetime
from pydantic import BaseModel, Field


# =========================
# 👤 USER SCHEMAS
# =========================

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


# =========================
# 🍽 MEAL SCHEMAS
# =========================

class MealCreate(BaseModel):
    name: str
    category: str
    calories: float
    protein: float
    carbs: float
    fat: float


class MealResponse(BaseModel):
    id: int
    name: str
    category: str
    calories: float
    protein: float
    carbs: float
    fat: float
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# =========================
# 🎯 GOAL SCHEMAS
# =========================

class GoalCreate(BaseModel):
    calorie_goal: float
    protein_goal: float
    carbs_goal: float
    fat_goal: float
    goal_source: str  # NEW


class GoalResponse(BaseModel):
    id: int
    calorie_goal: float
    protein_goal: float
    carbs_goal: float
    fat_goal: float
    goal_source: str  # NEW
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# =========================
# 🔐 PASSWORD RESET
# =========================

class ForgotPassword(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    token: str
    new_password: str


# =========================
# 👤 PROFILE HEALTH UPDATE
# =========================

class UpdateName(BaseModel):
    name: str


class UpdateEmail(BaseModel):
    email: str


class UpdateHealth(BaseModel):
    age: int
    gender: str
    height: float
    weight: float


class HealthResponse(BaseModel):
    age: int
    gender: str
    height_cm: float
    weight_kg: float
    bmi: float
    category: str
    activity_level: str
    recommended_calories: float

    class Config:
        from_attributes = True


# =========================
# 🧠 SMART BMI SYSTEM
# =========================

class SmartBMIRequest(BaseModel):
    height_cm: float = Field(gt=0)
    weight_kg: float = Field(gt=0)
    age: int = Field(gt=0)
    gender: str
    activity_level: str


class SmartBMIResponse(BaseModel):
    bmi: float
    category: str
    bmr: float
    tdee: float
    recommended_calories: float
    protein_grams: float
    carbs_grams: float
    fat_grams: float
    recommendation: str


# =========================
# 🥗 MULTI FOOD NUTRITION
# =========================

from typing import List


class FoodNutrition(BaseModel):
    food_name: str
    display_name: str
    quantity: float
    unit: str
    calculated_weight_grams: float
    calories: float
    protein: float
    fat: float
    carbs: float


class MultiFoodNutritionResponse(BaseModel):
    foods: List[FoodNutrition]


# =========================
# CHANGE PASSWORD
# =========================

class ChangePassword(BaseModel):
    current_password: str
    new_password: str
    
    
# =========================
# Notification
# =========================    

class NotificationResponse(BaseModel):
    id: int
    message: str
    type: str
    is_read: int
    created_at: datetime

    class Config:
        from_attributes = True
        
class NotificationSettingsBase(BaseModel):
    enabled: bool
    meal_reminders: bool
    smart_mode: bool


class NotificationSettingsResponse(NotificationSettingsBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True
        
        
