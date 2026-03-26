from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.database import Base


# =========================
# 👤 USER MODEL
# =========================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # 🔗 Relationships
    meals = relationship("Meal", back_populates="user", cascade="all, delete")
    goals = relationship("UserGoal", back_populates="user", cascade="all, delete")
    bmi_records = relationship("BMIRecord", back_populates="user", cascade="all, delete")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete")
    settings = relationship("NotificationSettings", back_populates="user", uselist=False, cascade="all, delete")
    device_tokens = relationship("DeviceToken", back_populates="user", cascade="all, delete")


# =========================
# 🍽 MEAL MODEL
# =========================
class Meal(Base):
    __tablename__ = "meals"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    category = Column(String, nullable=False)

    calories = Column(Float, default=0, nullable=False)
    protein = Column(Float, default=0, nullable=False)
    carbs = Column(Float, default=0, nullable=False)
    fat = Column(Float, default=0, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="meals")


# =========================
# 🎯 USER GOALS MODEL
# =========================
class UserGoal(Base):
    __tablename__ = "user_goals"

    id = Column(Integer, primary_key=True, index=True)

    calorie_goal = Column(Float, default=2000, nullable=False)
    protein_goal = Column(Float, default=100, nullable=False)
    carbs_goal = Column(Float, default=250, nullable=False)
    fat_goal = Column(Float, default=70, nullable=False)

    goal_source = Column(String, default="manual")

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="goals")


# =========================
# 🧠 BMI RECORD MODEL
# =========================
class BMIRecord(Base):
    __tablename__ = "bmi_records"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    age = Column(Integer)
    gender = Column(String)

    height_cm = Column(Float)
    weight_kg = Column(Float)

    bmi = Column(Float)
    category = Column(String)
    activity_level = Column(String)
    recommended_calories = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bmi_records")


# =========================
# 🔔 NOTIFICATION MODEL
# =========================
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    message = Column(String, nullable=False)
    type = Column(String, default="info")  # success | warning | info

    is_read = Column(Boolean, default=False)  # ✅ FIXED

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    user = relationship("User", back_populates="notifications")


# =========================
# ⚙️ NOTIFICATION SETTINGS
# =========================
class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    enabled = Column(Boolean, default=True)
    meal_reminders = Column(Boolean, default=True)
    smart_mode = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="settings")


# =========================
# 📱 DEVICE TOKENS (FCM)
# =========================
class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, nullable=False)

    user = relationship("User", back_populates="device_tokens")
    
    
# =========================
# 📅 DAILY GOALS MODEL
# =========================
from sqlalchemy import Date  # ✅ add this import at top if not present

class DailyGoal(Base):
    __tablename__ = "daily_goals"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    goal_date = Column(Date, nullable=False)

    calorie_goal = Column(Float, default=0)
    protein_goal = Column(Float, default=0)
    carbs_goal = Column(Float, default=0)
    fat_goal = Column(Float, default=0)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # optional relationship (not required but good)
    user = relationship("User")