from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..database import get_db
from .. import models, schemas
from app.auth_utils import get_current_user
from datetime import date, timedelta  # ✅ added timedelta

router = APIRouter(prefix="/goals", tags=["Goals"])


# ===========================
# 🔥 NEW: FILL MISSING DAYS
# ===========================
def fill_missing_goal_days(db: Session, user_id: int):
    result = db.execute(
        text("""
        SELECT goal_date, calorie_goal, protein_goal, carbs_goal, fat_goal, goal_source
        FROM daily_goals
        WHERE user_id = :user_id
        ORDER BY goal_date ASC
        """),
        {"user_id": user_id}
    ).fetchall()

    if not result:
        return

    last_entry = result[0]

    for i in range(1, len(result)):
        current = result[i]

        prev_date = last_entry.goal_date
        curr_date = current.goal_date

        next_day = prev_date + timedelta(days=1)

        while next_day < curr_date:
            db.execute(
                text("""
                INSERT INTO daily_goals
                (user_id, goal_date, calorie_goal, protein_goal, carbs_goal, fat_goal, goal_source)
                VALUES (:user_id, :goal_date, :calorie_goal, :protein_goal, :carbs_goal, :fat_goal, :goal_source)
                ON CONFLICT (user_id, goal_date) DO NOTHING
                """),
                {
                    "user_id": user_id,
                    "goal_date": next_day,
                    "calorie_goal": last_entry.calorie_goal,
                    "protein_goal": last_entry.protein_goal,
                    "carbs_goal": last_entry.carbs_goal,
                    "fat_goal": last_entry.fat_goal,
                    "goal_source": last_entry.goal_source,
                }
            )
            next_day += timedelta(days=1)

        last_entry = current

    db.commit()


# ===========================
# GET CURRENT USER GOAL
# ===========================
@router.get("/", response_model=schemas.GoalResponse)
def get_current_goal(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    goal = (
        db.query(models.UserGoal)
        .filter(models.UserGoal.user_id == current_user.id)
        .first()
    )

    if not goal:
        goal = models.UserGoal(
            user_id=current_user.id,
            calorie_goal=0,
            protein_goal=0,
            carbs_goal=0,
            fat_goal=0,
            goal_source="manual"
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)

    return goal


# ===========================
# UPDATE (OR CREATE) GOAL
# ===========================
@router.put("/", response_model=schemas.GoalResponse)
def update_goal(
    goal_data: schemas.GoalCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    goal = (
        db.query(models.UserGoal)
        .filter(models.UserGoal.user_id == current_user.id)
        .first()
    )

    if not goal:
        goal = models.UserGoal(
            user_id=current_user.id,
            goal_source="manual"
        )
        db.add(goal)

    # Update values
    goal.calorie_goal = goal_data.calorie_goal
    goal.protein_goal = goal_data.protein_goal
    goal.carbs_goal = goal_data.carbs_goal
    goal.fat_goal = goal_data.fat_goal
    goal.goal_source = goal_data.goal_source

    # ==============================
    # SAVE DAILY GOAL SNAPSHOT
    # ==============================

    today = date.today()

    db.execute(
        text("""
        INSERT INTO daily_goals
        (user_id, goal_date, calorie_goal, protein_goal, carbs_goal, fat_goal, goal_source)
        VALUES (:user_id, :goal_date, :calorie_goal, :protein_goal, :carbs_goal, :fat_goal, :goal_source)
        ON CONFLICT (user_id, goal_date)
        DO UPDATE SET
        calorie_goal = EXCLUDED.calorie_goal,
        protein_goal = EXCLUDED.protein_goal,
        carbs_goal = EXCLUDED.carbs_goal,
        fat_goal = EXCLUDED.fat_goal,
        goal_source = EXCLUDED.goal_source
        """),
        {
            "user_id": current_user.id,
            "goal_date": today,
            "calorie_goal": goal_data.calorie_goal,
            "protein_goal": goal_data.protein_goal,
            "carbs_goal": goal_data.carbs_goal,
            "fat_goal": goal_data.fat_goal,
            "goal_source": goal_data.goal_source,
        }
    )

    db.commit()
    db.refresh(goal)

    return goal


# ==============================
# FETCH GOAL HISTORY (UPDATED)
# ==============================

@router.get("/history")
def get_goal_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 🔥 NEW: auto-fill missing days
    fill_missing_goal_days(db, current_user.id)

    result = db.execute(
        text("""
        SELECT goal_date,
               calorie_goal,
               protein_goal,
               carbs_goal,
               fat_goal
        FROM daily_goals
        WHERE user_id = :user_id
        ORDER BY goal_date ASC
        """),
        {"user_id": current_user.id}
    )

    goals = result.fetchall()

    return [
        {
            "goal_date": g.goal_date.isoformat() if g.goal_date else None,
            "calorie_goal": g.calorie_goal,
            "protein_goal": g.protein_goal,
            "carbs_goal": g.carbs_goal,
            "fat_goal": g.fat_goal,
        }
        for g in goals
    ]