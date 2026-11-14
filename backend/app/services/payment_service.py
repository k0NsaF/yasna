
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import (
    Payment,
    Subscription,
    LessonTransaction,
)


def create_payment(
    db: Session,
    family_id: int,
    subscription_id: int,
    amount: Decimal,
    payment_method: str = "demo",
):
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.family_id == family_id,
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=404,
            detail="Абонемент не найден в вашей семье",
        )

    if subscription.is_active:
        raise HTTPException(
            status_code=409,
            detail="Абонемент уже активирован",
        )

    if payment_method != "demo":
        raise HTTPException(
            status_code=400,
            detail="В этой версии доступна только демонстрационная оплата",
        )

    if amount != subscription.price:
        raise HTTPException(
            status_code=400,
            detail="Сумма платежа не совпадает со стоимостью абонемента",
        )

    payment = Payment(
        family_id=family_id,
        subscription_id=subscription_id,
        amount=amount,
        status="pending",
        payment_method=payment_method,
        credited=False,
    )

    try:
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment
    except Exception:
        db.rollback()
        raise


def get_family_payments(db: Session, family_id: int):
    return (
        db.query(Payment)
        .filter(Payment.family_id == family_id)
        .order_by(Payment.created_at.desc())
        .all()
    )


def get_all_payments(db: Session):
    return (
        db.query(Payment)
        .order_by(Payment.created_at.desc())
        .all()
    )


def update_payment_status(
    db: Session,
    payment_id: int,
    new_status: str,
):
    if new_status not in {"succeeded", "failed", "cancelled"}:
        raise HTTPException(
            status_code=400,
            detail="Недопустимый статус платежа",
        )

    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Платёж не найден",
        )

    # Повторное подтверждение не начисляет занятия повторно.
    if payment.credited:
        if new_status == "succeeded":
            return payment

        raise HTTPException(
            status_code=409,
            detail="Уже подтверждённый платёж нельзя отменить этим способом",
        )

    if payment.status != "pending":
        raise HTTPException(
            status_code=409,
            detail="Этот платёж уже обработан",
        )

    if new_status == "succeeded":
        subscription = None

        if payment.subscription_id is not None:
            subscription = db.query(Subscription).filter(
                Subscription.id == payment.subscription_id,
                Subscription.family_id == payment.family_id,
            ).first()

            if not subscription:
                raise HTTPException(
                    status_code=404,
                    detail="Абонемент платежа не найден",
                )

            if subscription.is_active:
                raise HTTPException(
                    status_code=409,
                    detail="Абонемент уже активирован другим платежом",
                )

            # Активируем абонемент.
            subscription.is_active = True

            # Начисляем занятия только один раз.
            db.add(LessonTransaction(
                subscription_id=subscription.id,
                booking_id=None,
                amount=subscription.total_lessons,
                operation="grant",
                reason="Начисление после подтверждения оплаты",
            ))

        payment.status = "succeeded"
        payment.credited = True

    else:
        payment.status = new_status

    try:
        db.commit()
        db.refresh(payment)
        return payment
    except Exception:
        db.rollback()
        raise
