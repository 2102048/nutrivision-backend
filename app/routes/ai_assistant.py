from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
import requests
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import smtplib
from email.mime.text import MIMEText
from dateutil import parser
import re

from app.database import get_db
from app.models import User, Meal, UserGoal, BMIRecord, DailyGoal  # ✅ ADDED DailyGoal
from app.auth_utils import get_current_user

load_dotenv()

router = APIRouter()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# =========================
# SESSION MEMORY
# =========================
user_sessions = {}

# =========================
# REQUEST MODEL
# =========================
class AIQuestion(BaseModel):
    message: str
    session_id: str = "default"

# =========================
# HELPERS
# =========================
def normalize_text(text: str):
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)

    fixes = {
        "heat": "eat",
        "atee": "ate",
        "caloriee": "calorie",
        "complet": "complete",
        "waht": "what",
        "hw": "how",
        "cal": "calories"
    }

    for k, v in fixes.items():
        text = text.replace(k, v)

    return text

def extract_date_from_text(text: str):
    try:
        return parser.parse(text, fuzzy=True).date()
    except:
        return None

def meals_to_names(meals):
    if not meals:
        return ""
    return ", ".join([m.name for m in meals])

def meals_to_text(meals):
    if not meals:
        return "No meals logged."
    return "\n".join([f"- {m.name} ({m.calories} cal)" for m in meals])

def total_cal(meals):
    return sum(m.calories or 0 for m in meals)

def calorie_comparison(consumed, goal, day_str):
    if not goal:
        return f"You consumed {consumed} calories on {day_str}."

    diff = consumed - goal

    if diff > 0:
        return f"You consumed {consumed} calories on {day_str}. That is {diff} calories ABOVE your goal ⚠️"
    elif diff < 0:
        return f"You consumed {consumed} calories on {day_str}. You are {abs(diff)} calories BELOW your goal."
    else:
        return f"You consumed {consumed} calories on {day_str}. You perfectly met your goal 🎯"

# =========================
# 🔥 FIXED GOAL FETCH (DAILY + FALLBACK)
# =========================
def get_goal_for_day(db, user_id, day):
    # 1️⃣ Check daily_goals first
    daily = db.query(DailyGoal).filter(
        DailyGoal.user_id == user_id,
        DailyGoal.goal_date == day
    ).first()

    if daily:
        return daily

    # 2️⃣ fallback → user_goals
    fallback = db.query(UserGoal).filter(
        UserGoal.user_id == user_id
    ).order_by(UserGoal.id.desc()).first()

    return fallback


# =========================
# 🔥 SMART INTENT DETECTION
# =========================
def match_patterns(text, patterns):
    return any(re.search(p, text) for p in patterns)

def is_ai_identity_query(text):
    return match_patterns(text, [
        r"who are you",
        r"what are you",
        r"your name"
    ])

def is_name_query(text):
    return match_patterns(text, [
        r"my name",
        r"who am i",
        r"what.*my name",
        r"tell.*my name",
        r"do you know my name",
        r"remember my name"
    ])

def is_profile_query(text):
    return match_patterns(text, [
        r"my age",
        r"how old am i",
        r"my height",
        r"my weight",
        r"my bmi",
        r"what is my (age|height|weight|bmi|gender)"
    ])

def is_food_query(text):
    return match_patterns(text, [
        r"what.*(eat|ate|had|consume)",
        r"(eat|ate|had).*what",
        r"what did i (eat|have|consume)",
        r"list.*(food|meal)",
        r"(food|meal).*on",
        r"what was my (breakfast|lunch|dinner)",
        r"did i eat anything"
    ])

def is_calorie_consumed_query(text):
    return match_patterns(text, [
        r"how many calories",
        r"calories did i (eat|consume|have)",
        r"total calories",
        r"how much did i eat",
        r"calorie intake"
    ]) and "goal" not in text

def is_goal_completion_query(text):
    return match_patterns(text, [
        r"did i hit",
        r"did i reach",
        r"goal (met|achieved|completed)",
        r"am i over my goal",
        r"did i exceed"
    ])

def is_calorie_goal_query(text):
    return match_patterns(text, [
        r"calorie[s]? goal",
        r"goal.*calorie",
        r"calorie.*goal",
        r"target calories?",
        r"daily goal",
        r"goal for (today|yesterday|\d{1,2})",
        r"what.*goal",
        r"my goal",
        r"how many calories.*goal"
    ])

def is_calorie_remaining_query(text):
    return match_patterns(text, [
        r"remaining",
        r"calories left",
        r"how much can i eat",
        r"left to eat",
        r"how many calories left"
    ])

def is_email_query(text):
    return match_patterns(text, [
        r"email",
        r"send mail",
        r"send report"
    ])

# =========================
# EMAIL
# =========================
def send_email(to_email, subject, body):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = to_email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()

        return True
    except Exception as e:
        print("Email error:", e)
        return False

# =========================
# MAIN ROUTE
# =========================
@router.post("/ai-assistant")
def ai_assistant(
    question: AIQuestion,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        user = current_user
        user_q_raw = question.message
        user_q = normalize_text(user_q_raw)

        session_id = question.session_id
        if session_id not in user_sessions:
            user_sessions[session_id] = []
        history = user_sessions[session_id]

        # =========================
        # DATE
        # =========================
        today = date.today()
        yesterday = today - timedelta(days=1)
        custom_date = extract_date_from_text(user_q)

        def resolve_day():
            if custom_date:
                return custom_date, custom_date.strftime('%d %B %Y')
            if "yesterday" in user_q:
                return yesterday, "yesterday"
            if "today" in user_q:
                return today, "today"
            return today, "today"

        target_day, day_str = resolve_day()

        def get_meals(day):
            start = datetime.combine(day, datetime.min.time())
            end = datetime.combine(day + timedelta(days=1), datetime.min.time())
            return db.query(Meal).filter(
                Meal.user_id == user.id,
                Meal.created_at >= start,
                Meal.created_at < end
            ).all()

        meals = get_meals(target_day)
        today_meals = get_meals(today)

        consumed = total_cal(meals)
        today_cal = total_cal(today_meals)

        # ✅ FIXED GOAL LOGIC
        goal_for_day = get_goal_for_day(db, user.id, target_day)
        today_goal = get_goal_for_day(db, user.id, today)

        def extract_cal(goal):
            return getattr(goal, "calorie_goal", None) if goal else None

        calorie_goal = extract_cal(goal_for_day)
        today_calorie_goal = extract_cal(today_goal)

        remaining = (today_calorie_goal - today_cal) if today_calorie_goal else None

        bmi_record = db.query(BMIRecord).filter(
            BMIRecord.user_id == user.id
        ).order_by(BMIRecord.created_at.desc()).first()

        age = bmi_record.age if bmi_record else "Not set"
        height = bmi_record.height_cm if bmi_record else "Not set"
        weight = bmi_record.weight_kg if bmi_record else "Not set"
        bmi = bmi_record.bmi if bmi_record else "Not set"
        gender = bmi_record.gender if bmi_record and hasattr(bmi_record, "gender") else "Not set"

        # =========================
        # ROUTING
        # =========================
        if is_ai_identity_query(user_q):
            return {"reply": "I am NutriVision AI, your personal nutrition assistant."}

        if is_name_query(user_q):
            return {"reply": f"Your name is {user.name}."}

        if is_profile_query(user_q):
            if "age" in user_q:
                return {"reply": f"Your age is {age}."}
            if "height" in user_q:
                return {"reply": f"Your height is {height} cm."}
            if "weight" in user_q:
                return {"reply": f"Your weight is {weight} kg."}
            if "bmi" in user_q:
                return {"reply": f"Your BMI is {bmi}."}
            if "gender" in user_q:
                return {"reply": f"Your gender is {gender}."}

        if is_food_query(user_q):
            if meals:
                return {"reply": f"You ate {meals_to_names(meals)} on {day_str}."}
            else:
                return {"reply": f"No meals logged on {day_str}."}

        if is_calorie_consumed_query(user_q):
            return {"reply": calorie_comparison(consumed, calorie_goal, day_str)}

        if is_goal_completion_query(user_q):
            if not calorie_goal:
                return {"reply": f"You had no calorie goal set on {day_str}."}

            if consumed >= calorie_goal:
                return {"reply": f"Yes, you exceeded your goal by {consumed - calorie_goal} calories on {day_str}."}
            else:
                return {"reply": f"No, you were {calorie_goal - consumed} calories below your goal on {day_str}."}

        if is_calorie_goal_query(user_q):
            if not calorie_goal:
                return {"reply": f"You had no calorie goal set on {day_str}."}
            return {"reply": f"Your calorie goal on {day_str} was {calorie_goal} calories."}

        if is_calorie_remaining_query(user_q):
            if not today_calorie_goal:
                return {"reply": "You have not set a calorie goal for today."}
            return {"reply": f"You need {remaining} more calories to reach your goal today."}

        if is_email_query(user_q):
            if not user.email:
                return {"reply": "No email found."}

            body = f"""
Hello {user.name},

Calories Today: {today_cal}
BMI: {bmi}
Weight: {weight} kg
Gender: {gender}

- NutriVision AI
"""
            success = send_email(user.email, "Nutrition Report", body)
            return {"reply": "Email sent successfully." if success else "Failed to send email."}

        if "name" in user_q:
            return {"reply": f"Your name is {user.name}."}

        # =========================
        # AI FALLBACK
        # =========================
        context = f"""
You are NutriVision AI.

User: {user.name}
Gender: {gender}
BMI: {bmi}

Meals:
{meals_to_text(today_meals)}

Answer shortly and clearly.
"""

        messages = [{"role": "system", "content": context}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_q_raw})

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-3.5-turbo",
                "messages": messages
            }
        )

        result = response.json()
        reply = result["choices"][0]["message"]["content"]

        history.append({"role": "user", "content": user_q_raw})
        history.append({"role": "assistant", "content": reply})
        user_sessions[session_id] = history[-10:]

        return {"reply": reply}

    except Exception as e:
        return {"reply": f"AI assistant error: {str(e)}"}