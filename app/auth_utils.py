from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
from email.mime.text import MIMEText
import smtplib
import os

from app import schemas

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

# ===============================
# LOAD ENV VARIABLES
# ===============================

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


# ===============================
# PASSWORD HASHING
# ===============================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str) -> str:
    """
    Hash a plain password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


# ===============================
# AUTH TOKEN SYSTEM
# ===============================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def create_access_token(data: dict) -> str:
    """
    Create login JWT token
    """
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(days=7)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt


# ===============================
# PASSWORD RESET TOKEN
# ===============================

def create_reset_token(email: str) -> str:
    """
    Create short-lived password reset token
    """

    expire = datetime.utcnow() + timedelta(minutes=10)

    to_encode = {
        "sub": email,
        "exp": expire
    }

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def verify_token(token: str):
    """
    Verify JWT token and return payload
    """

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload

    except JWTError:

        return None


# ===============================
# SEND RESET EMAIL
# ===============================

def send_reset_email(to_email: str, reset_token: str):
    """
    Send password reset email
    """

    try:

        reset_link = f"http://localhost:5173/reset-password/{reset_token}"

        subject = "NutriVision Password Reset"

        body = f"""
Click the link below to reset your password:

{reset_link}

This link expires in 10 minutes.
"""

        msg = MIMEText(body)

        msg["Subject"] = subject
        msg["From"] = SMTP_EMAIL
        msg["To"] = to_email

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)

        server.starttls()

        server.login(SMTP_EMAIL, SMTP_PASSWORD)

        server.sendmail(
            SMTP_EMAIL,
            to_email,
            msg.as_string()
        )

        server.quit()

        print("Reset email sent successfully")

    except Exception as e:

        print("Email sending failed:", e)


# ===============================
# GET CURRENT LOGGED USER
# ===============================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Extract logged-in user from JWT token
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        email: str = payload.get("sub")

        if email is None:
            raise credentials_exception

    except JWTError as e:
        print("JWT ERROR:", str(e))
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()

    if user is None:
        raise credentials_exception

    return user

schemas.ForgotPassword
schemas.ResetPassword
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
    goal_type: str = "maintain"


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
        
