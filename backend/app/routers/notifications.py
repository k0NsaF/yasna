
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..security import get_current_master, get_current_family
from ..models import Notification, Family
from ..schemas import NotificationResponse


router = APIRouter(tags=["Уведомления"])


class NotificationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=2000)


# Мастер отправляет уведомление конкретной семье.
@router.post(
    "/api/master/families/{family_id}/notifications",
    response_model=NotificationResponse
)
def create_notification(
    family_id: int,
    payload: NotificationCreate,
    db: Session = Depends(get_db),
    master=Depends(get_current_master)
):
    family = db.query(Family).filter(
        Family.id == family_id
    ).first()

    if not family:
        raise HTTPException(
            status_code=404,
            detail="Семья не найдена"
        )

    notification = Notification(
        family_id=family_id,
        title=payload.title,
        message=payload.message,
        is_read=False
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification


# Родитель получает уведомления только своей семьи.
@router.get(
    "/api/family/notifications",
    response_model=list[NotificationResponse]
)
def get_family_notifications(
    db: Session = Depends(get_db),
    family=Depends(get_current_family)
):
    return (
        db.query(Notification)
        .filter(Notification.family_id == family.id)
        .order_by(Notification.created_at.desc())
        .all()
    )


# Родитель отмечает одно уведомление прочитанным.
@router.patch(
    "/api/family/notifications/{notification_id}/read",
    response_model=NotificationResponse
)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    family=Depends(get_current_family)
):
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.family_id == family.id
        )
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Уведомление не найдено"
        )

    notification.is_read = True

    db.commit()
    db.refresh(notification)

    return notification


# Родитель отмечает все свои уведомления прочитанными.
@router.patch("/api/family/notifications/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    family=Depends(get_current_family)
):
    db.query(Notification).filter(
        Notification.family_id == family.id,
        Notification.is_read.is_(False)
    ).update(
        {Notification.is_read: True},
        synchronize_session=False
    )

    db.commit()

    return {
        "status": "ok",
        "message": "Все уведомления отмечены прочитанными"
    }
