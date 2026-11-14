
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import (
    Family,
    Child,
    Subscription,
)


def create_subscription(db: Session, payload):
    family = db.query(Family).filter(
        Family.id == payload.family_id
    ).first()

    if not family:
        raise HTTPException(
            status_code=404,
            detail="Семья не найдена",
        )

    if payload.child_id is not None:
        child = db.query(Child).filter(
            Child.id == payload.child_id,
            Child.family_id == payload.family_id,
        ).first()

        if not child:
            raise HTTPException(
                status_code=404,
                detail="Ребёнок не найден в указанной семье",
            )

    subscription = Subscription(
        family_id=payload.family_id,
        child_id=payload.child_id,
        title=payload.title,
        total_lessons=payload.total_lessons,
        used_lessons=0,
        price=payload.price,
        expires_at=payload.expires_at,
        is_active=False,
    )

    try:
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        return subscription

    except Exception:
        db.rollback()
        raise


def get_family_subscriptions(db: Session, family_id: int):
    return (
        db.query(Subscription)
        .filter(Subscription.family_id == family_id)
        .order_by(Subscription.created_at.desc())
        .all()
    )


def get_all_subscriptions(db: Session):
    return (
        db.query(Subscription)
        .order_by(Subscription.created_at.desc())
        .all()
    )


def deactivate_subscription(db: Session, subscription_id: int):
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=404,
            detail="Абонемент не найден",
        )

    subscription.is_active = False

    try:
        db.commit()
        db.refresh(subscription)
        return subscription

    except Exception:
        db.rollback()
        raise


def get_family_subscription_balance(db: Session, family_id: int):
    now = datetime.utcnow()

    subscriptions = (
        db.query(Subscription)
        .filter(
            Subscription.family_id == family_id,
            Subscription.is_active.is_(True),
        )
        .all()
    )

    total_lessons = 0
    used_lessons = 0
    remaining_lessons = 0

    for subscription in subscriptions:
        if (
            subscription.expires_at is not None
            and subscription.expires_at.replace(tzinfo=None) <= now
        ):
            continue

        total_lessons += subscription.total_lessons
        used_lessons += subscription.used_lessons

        remaining_lessons += max(
            0,
            subscription.total_lessons - subscription.used_lessons,
        )

    return {
        "total_lessons": total_lessons,
        "used_lessons": used_lessons,
        "remaining_lessons": remaining_lessons,
        "money_balance": 0,
    }
