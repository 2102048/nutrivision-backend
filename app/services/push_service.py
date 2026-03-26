from firebase_admin import messaging
from app import models


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

        messaging.send(message)