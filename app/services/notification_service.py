from firebase_admin import messaging
from datetime import datetime

from app import models


# =========================
# 📤 SEND PUSH
# =========================
def send_push(db, user_id, title, body):
    tokens = db.query(models.DeviceToken).filter(
        models.DeviceToken.user_id == user_id
    ).all()

    for t in tokens:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=t.token,
        )

        try:
            messaging.send(message)
        except Exception as e:
            print("FCM Error:", e)


# =========================
# 🧠 MAIN NOTIFICATION ENGINE
# =========================
def check_goal_notifications(db, user_id):

    print("🔥 FUNCTION CALLED")

    created_notifications = []

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        print("❌ User not found")
        return []

    # =========================
    # 🔕 SETTINGS CHECK
    # =========================
    settings = db.query(models.NotificationSettings).filter(
        models.NotificationSettings.user_id == user_id
    ).first()

    if not settings or not settings.enabled:
        print("🔕 Notifications disabled")
        return []

    now = datetime.utcnow()
    today_str = now.strftime("%Y-%m-%d")

    # =========================
    # ⛔ PREVENT MULTIPLE RUNS
    # =========================
    if user.last_notification_date == today_str:
        print("⛔ Already notified today")
        return []

    # ============================================================
    # 🍽️ MEAL REMINDERS (TIME-BASED)
    # ============================================================
    if settings.meal_reminders:
        current_hour = now.hour

        if current_hour in [9, 13, 20]:  # breakfast, lunch, dinner
            reminder_msg = "Don't forget to log your meal 🍽️"

            notification = models.Notification(
                user_id=user_id,
                message=reminder_msg,
                type="info",
                is_read=False
            )

            db.add(notification)
            db.commit()
            db.refresh(notification)

            created_notifications.append(notification)

            print("⏰ Meal reminder sent")

            send_push(
                db,
                user_id,
                "Meal Reminder 🍽️",
                reminder_msg
            )

            return created_notifications  # stop here for reminders

    # ============================================================
    # 🧠 SMART AI NOTIFICATIONS
    # ============================================================
    if not settings.smart_mode:
        print("🧠 Smart AI disabled")
        return []

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    meals = db.query(models.Meal).filter(
        models.Meal.user_id == user_id,
        models.Meal.created_at >= today_start
    ).all()

    total_calories = sum(m.calories for m in meals)
    total_protein = sum(m.protein for m in meals)

    goal = db.query(models.UserGoal).filter(
        models.UserGoal.user_id == user_id
    ).order_by(models.UserGoal.created_at.desc()).first()

    if not goal:
        print("⚠️ No goal found")
        return []

    messages = []

    # 🔥 PROTEIN CHECK
    if total_protein < goal.protein_goal:
        remaining = int(goal.protein_goal - total_protein)
        messages.append(f"Low protein today (need {remaining}g more)")

    # 🔥 CALORIE CHECK
    if total_calories < goal.calorie_goal:
        messages.append("You're behind your calorie goal")

    if not messages:
        print("✅ All goals met")
        return []

    final_message = " | ".join(messages)

    if user.last_notification_message == final_message:
        print("⛔ Duplicate message blocked")
        return []

    try:
        fresh_user = db.query(models.User).filter(
            models.User.id == user_id
        ).with_for_update().first()

        if fresh_user.last_notification_date == today_str:
            return []

        notification = models.Notification(
            user_id=user_id,
            message=final_message,
            type="warning",
            is_read=False
        )

        db.add(notification)

        fresh_user.last_notification_date = today_str
        fresh_user.last_notification_message = final_message

        db.commit()
        db.refresh(notification)

        created_notifications.append(notification)

        print("🚀 Smart notification sent")

    except Exception as e:
        db.rollback()
        print("❌ DB Error:", e)
        return []

    # =========================
    # 📲 PUSH
    # =========================
    send_push(
        db,
        user_id,
        "Nutrition Alert ⚠️",
        final_message
    )

    return created_notifications