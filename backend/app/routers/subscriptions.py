
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Family, Child, Subscription
from ..schemas import (
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionBalance,
)
from ..security import get_current_master, get_current_family


router = APIRouter(tags=["Абонементы"])


# ---------- МАСТЕР ----------

# Мастер создаёт новый абонемент.
# До оплаты он неактивен.
@router.post(
    "/api/master/subscriptions",
    response_model=SubscriptionResponse,
)
def create_subscription(
    payload: SubscriptionCreate,
    db: Session = Depends(get_db),
    master=Depends(get_current_master),
):
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
                detail="Ребёнок не найден в этой семье",
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


# Мастер смотрит все абонементы.
@router.get(
    "/api/master/subscriptions",
    response_model=list[SubscriptionResponse],
)
def get_all_subscriptions(
    db: Session = Depends(get_db),
    master=Depends(get_current_master),
):
    return (
        db.query(Subscription)
        .order_by(Subscription.created_at.desc())
        .all()
    )


# ---------- РОДИТЕЛЬ ----------

# Родитель видит абонементы только своей семьи.
@router.get(
    "/api/family/subscriptions",
    response_model=list[SubscriptionResponse],
)
def get_family_subscriptions(
    db: Session = Depends(get_db),
    family=Depends(get_current_family),
):
    return (
        db.query(Subscription)
        .filter(Subscription.family_id == family.id)
        .order_by(Subscription.created_at.desc())
        .all()
    )


# Родитель видит общий баланс занятий своей семьи.
@router.get(
    "/api/family/subscriptions/balance",
    response_model=SubscriptionBalance,
)
def get_family_subscription_balance(
    db: Session = Depends(get_db),
    family=Depends(get_current_family),
):
    subscriptions = (
        db.query(Subscription)
        .filter(
            Subscription.family_id == family.id,
            Subscription.is_active.is_(True),
        )
        .all()
    )

    total = sum(
        item.total_lessons for item in subscriptions
    )

    used = sum(
        item.used_lessons for item in subscriptions
    )

    return {
        "total_lessons": total,
        "used_lessons": used,
        "remaining_lessons": max(0, total - used),
        "money_balance": 0,
    }
