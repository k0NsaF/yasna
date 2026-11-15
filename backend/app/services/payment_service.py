
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import (
    Payment,
    Subscription,
    LessonTransaction,
    Booking,
    Child,
    Lesson,
)


def create_payment(
    db: Session,
    family_id: int,
    subscription_id: int = None,
    booking_id: int = None,
    amount: Decimal = Decimal("0"),
    payment_method: str = "demo",
):
    # Должен быть указан ровно один вариант оплаты:
    # либо абонемент, либо конкретная запись.
    if (subscription_id is None) == (booking_id is None):
        raise HTTPException(
            status_code=400,
            detail="Укажите абонемент или запись на занятие",
        )

    if payment_method != "demo":
        raise HTTPException(
            status_code=400,
            detail="Доступна только демонстрационная оплата",
        )

    if amount < 0:
        raise HTTPException(
            status_code=400,
            detail="Сумма платежа не может быть отрицательной",
        )

    # -----------------------------------------
    # ВАРИАНТ 1. ОПЛАТА АБОНЕМЕНТА
    # -----------------------------------------
    if subscription_id is not None:
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

        if amount != subscription.price:
            raise HTTPException(
                status_code=400,
                detail="Сумма платежа не совпадает со стоимостью абонемента",
            )

        existing_payment = db.query(Payment).filter(
            Payment.subscription_id == subscription_id,
            Payment.status.in_(["pending", "succeeded"]),
        ).first()

        if existing_payment:
            raise HTTPException(
                status_code=409,
                detail="Для этого абонемента уже существует ожидающий или успешный платёж",
            )

        payment = Payment(
            family_id=family_id,
            subscription_id=subscription_id,
            booking_id=None,
            amount=amount,
            status="pending",
            payment_method=payment_method,
            credited=False,
        )

    # -----------------------------------------
    # ВАРИАНТ 2. РАЗОВАЯ ОПЛАТА ЗАНЯТИЯ
    # -----------------------------------------
    else:
        booking = (
            db.query(Booking)
            .join(Child, Booking.child_id == Child.id)
            .filter(
                Booking.id == booking_id,
                Child.family_id == family_id,
            )
            .first()
        )

        if not booking:
            raise HTTPException(
                status_code=404,
                detail="Запись на занятие не найдена в вашей семье",
            )

        if booking.status != "booked":
            raise HTTPException(
                status_code=409,
                detail="Нельзя оплатить отменённую запись",
            )

        lesson = db.query(Lesson).filter(
            Lesson.id == booking.lesson_id
        ).first()

        if not lesson:
            raise HTTPException(
                status_code=404,
                detail="Занятие не найдено",
            )

        if amount != lesson.price:
            raise HTTPException(
                status_code=400,
                detail="Сумма платежа не совпадает со стоимостью занятия",
            )

        existing_payment = db.query(Payment).filter(
            Payment.booking_id == booking_id,
            Payment.status.in_(["pending", "succeeded"]),
        ).first()

        if existing_payment:
            raise HTTPException(
                status_code=409,
                detail="Для этой записи уже существует ожидающий или успешный платёж",
            )

        payment = Payment(
            family_id=family_id,
            subscription_id=None,
            booking_id=booking_id,
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

    # Защита от повторного подтверждения.
    if payment.credited:
        if new_status == "succeeded":
            return payment

        raise HTTPException(
            status_code=409,
            detail="Уже подтверждённый платёж нельзя отменить",
        )

    if payment.status != "pending":
        raise HTTPException(
            status_code=409,
            detail="Этот платёж уже обработан",
        )

    if new_status == "succeeded":

        # -------------------------------------
        # УСПЕШНАЯ ОПЛАТА АБОНЕМЕНТА
        # -------------------------------------
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

            subscription.is_active = True

            db.add(
                LessonTransaction(
                    subscription_id=subscription.id,
                    booking_id=None,
                    amount=subscription.total_lessons,
                    operation="grant",
                    reason="Начисление после подтверждения оплаты",
                )
            )

        # -------------------------------------
        # УСПЕШНАЯ РАЗОВАЯ ОПЛАТА
        # -------------------------------------
        elif payment.booking_id is not None:
            booking = (
                db.query(Booking)
                .join(Child, Booking.child_id == Child.id)
                .filter(
                    Booking.id == payment.booking_id,
                    Child.family_id == payment.family_id,
                )
                .first()
            )

            if not booking:
                raise HTTPException(
                    status_code=404,
                    detail="Запись для платежа не найдена",
                )

            if booking.status != "booked":
                raise HTTPException(
                    status_code=409,
                    detail="Нельзя подтвердить оплату отменённой записи",
                )

            # Разовая оплата не активирует абонемент
            # и не создаёт списание занятий.

        else:
            raise HTTPException(
                status_code=400,
                detail="У платежа не указан абонемент или запись",
            )

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
