from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas
from app.database import get_db
from app.auth_utils import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# =========================
# 🔥 WEBSOCKET MANAGER
# =========================
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print("✅ WebSocket connected")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print("❌ WebSocket disconnected")

    async def broadcast(self, data: dict):
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except:
                disconnected.append(connection)

        # cleanup dead connections
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


# =========================
# ⚡ WEBSOCKET ENDPOINT
# =========================
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# =========================
# 📥 GET NOTIFICATIONS
# =========================
@router.get("/")
def get_notifications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id
    ).order_by(models.Notification.created_at.desc()).all()


# =========================
# ✅ MARK ALL READ
# =========================
@router.post("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    db.query(models.Notification).filter(
        models.Notification.user_id == user.id
    ).update({"is_read": True})

    db.commit()
    return {"message": "All notifications marked as read"}


# =========================
# ⚡ TRIGGER SMART CHECK
# =========================
@router.post("/trigger-check")
async def trigger_notifications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    from app.services.notification_service import check_goal_notifications

    new_notifications = check_goal_notifications(db, current_user.id)

    # 🔥 REAL-TIME PUSH
    if new_notifications:
        for n in new_notifications:
            await manager.broadcast({
                "id": n.id,
                "message": n.message,
                "type": getattr(n, "type", "info"),
                "is_read": False
            })

    return {"message": "Notification check complete"}


# =========================
# ⚙️ SETTINGS
# =========================
@router.get("/settings", response_model=schemas.NotificationSettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    settings = db.query(models.NotificationSettings).filter(
        models.NotificationSettings.user_id == current_user.id
    ).first()

    if not settings:
        settings = models.NotificationSettings(
            user_id=current_user.id,
            enabled=True,
            meal_reminders=True,
            smart_mode=True
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


@router.put("/settings", response_model=schemas.NotificationSettingsResponse)
def update_settings(
    data: schemas.NotificationSettingsBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    settings = db.query(models.NotificationSettings).filter(
        models.NotificationSettings.user_id == current_user.id
    ).first()

    if not settings:
        settings = models.NotificationSettings(user_id=current_user.id)
        db.add(settings)

    settings.enabled = data.enabled
    settings.meal_reminders = data.meal_reminders
    settings.smart_mode = data.smart_mode

    db.commit()
    db.refresh(settings)

    return settings


# =========================
# 📱 SAVE TOKEN
# =========================
class TokenRequest(BaseModel):
    token: str


@router.post("/save-token")
def save_token(
    data: TokenRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    existing = db.query(models.DeviceToken).filter(
        models.DeviceToken.token == data.token
    ).first()

    if not existing:
        db.add(models.DeviceToken(
            user_id=current_user.id,
            token=data.token
        ))
        db.commit()

    return {"message": "Token saved"}