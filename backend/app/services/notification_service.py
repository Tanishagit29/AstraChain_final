from typing import List
from sqlalchemy.orm import Session
from app.models.all_models import Notification
from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    type: str
    is_read: bool

    model_config = ConfigDict(from_attributes=True)


class NotificationService:
    @staticmethod
    def get_notifications(db: Session, unread_only: bool = False) -> List[NotificationOut]:
        query = db.query(Notification)
        if unread_only:
            query = query.filter(Notification.is_read == False)
        notifications = query.order_by(Notification.id.desc()).all()
        return [NotificationOut.model_validate(n) for n in notifications]

    @staticmethod
    def mark_as_read(db: Session, notification_id: int) -> bool:
        n = db.query(Notification).filter(Notification.id == notification_id).first()
        if n:
            n.is_read = True
            db.commit()
            return True
        return False
