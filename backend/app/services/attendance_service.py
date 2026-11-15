
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import (
    Booking,
    Child,
    Attendance,
    AttendanceHistory,
    Subscription,
    LessonTransaction,
    Payment,
)


VALID_STATUSES = {"attended", "missed", "cancelled"}


def mark_attendance(
    db: Session,
    booking_id: int,
    new_status: str,
    comment: str | None = None,
):
    if new_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Недопустимый статус посещаемости",
        )

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Запись не найдена",
        )

    if booking.status != "booked":
        raise HTTPException(
            status_code=400,
            detail="Нельзя отметить посещаемость отменённой записи",
        )

    attendance = db.query(Attendance).filter(
        Attendance.booking_id == booking_id
    ).first()

    old_status = attendance.status if attendance else None

    if old_status == new_status:
        return attendance

    try:
        if attendance is None:
            attendance = Attendance(
                booking_id=booking_id,
                status=new_status,
                marked_at=datetime.utcnow(),
            )
            db.add(attendance)
            db.flush()

        else:
            db.add(
                AttendanceHistory(
                    attendance_id=attendance.id,
                    old_status=old_status,
                    new_status=new_status,
                    changed_at=datetime.utcnow(),
                    comment=comment,
                )
            )

            attendance.status = new_status
            attendance.marked_at = datetime.utcnow()

        # Последняя операция по этому бронированию.
        last_transaction = (
            db.query(LessonTransaction)
            .filter(
                LessonTransaction.booking_id == booking_id
            )
            .order_by(
                LessonTransaction.created_at.desc(),
                LessonTransaction.id.desc(),
            )
            .first()
        )

        # Проверяем, оплачено ли занятие отдельно.
        one_time_payment = db.query(Payment).filter(
            Payment.booking_id == booking_id,
            Payment.status == "succeeded",
        ).first()

        # -----------------------------------------
        # РЕБЁНОК ПОСЕТИЛ ЗАНЯТИЕ
        # -----------------------------------------
        if new_status == "attended":

            # Разовая оплата: абонемент не расходуем.
            if one_time_payment:
                pass

            # Уже было списание — повторно не списываем.
            elif (
                last_transaction
                and last_transaction.operation == "use"
            ):
                pass

            # Ранее вернули занятие — списываем снова.
            elif (
                last_transaction
                and last_transaction.operation == "refund"
            ):
                subscription = db.query(Subscription).filter(
                    Subscription.id
                    == last_transaction.subscription_id
                ).first()

                if subscription:
                    if subscription.used_lessons >= subscription.total_lessons:
                        raise HTTPException(
                            status_code=409,
                            detail="В абонементе закончились занятия",
                        )

                    subscription.used_lessons += 1

                    db.add(
                        LessonTransaction(
                            subscription_id=subscription.id,
                            booking_id=booking_id,
                            amount=1,
                            operation="use",
                            reason="Повторное подтверждение посещения",
                        )
                    )

            else:
                child = db.query(Child).filter(
                    Child.id == booking.child_id
                ).first()

                if not child:
                    raise HTTPException(
                        status_code=404,
                        detail="Ребёнок не найден",
                    )

                # Сначала ищем личный абонемент,
                # затем общий абонемент семьи.
                subscription = (
                    db.query(Subscription)
                    .filter(
                        Subscription.family_id == child.family_id,
                        Subscription.is_active.is_(True),
                        Subscription.used_lessons
                        < Subscription.total_lessons,
                        (
                            (Subscription.child_id == child.id)
                            | (Subscription.child_id.is_(None))
                        ),
                        (
                            (Subscription.expires_at.is_(None))
                            | (Subscription.expires_at >= datetime.utcnow())
                        ),
                    )
                    .order_by(
                        Subscription.child_id.is_(None).asc(),
                        Subscription.created_at.desc(),
                    )
                    .first()
                )

                # Если абонемента нет, посещение всё равно фиксируем.
                if subscription:
                    subscription.used_lessons += 1

                    db.add(
                        LessonTransaction(
                            subscription_id=subscription.id,
                            booking_id=booking_id,
                            amount=1,
                            operation="use",
                            reason="Посещение занятия",
                        )
                    )

        # -----------------------------------------
        # ОТМЕНА ОТМЕТКИ О ПОСЕЩЕНИИ
        # -----------------------------------------
        elif old_status == "attended":

            # Разовая оплата не связана со списанием абонемента.
            if one_time_payment:
                pass

            elif (
                last_transaction
                and last_transaction.operation == "use"
            ):
                subscription = db.query(Subscription).filter(
                    Subscription.id
                    == last_transaction.subscription_id
                ).first()

                if subscription:
                    subscription.used_lessons = max(
                        0,
                        subscription.used_lessons - 1,
                    )

                    db.add(
                        LessonTransaction(
                            subscription_id=subscription.id,
                            booking_id=booking_id,
                            amount=1,
                            operation="refund",
                            reason="Возврат занятия после изменения посещаемости",
                        )
                    )

        db.commit()
        db.refresh(attendance)

        return attendance

    except Exception:
        db.rollback()
        raise


def get_attendance_history(
    db: Session,
    booking_id: int,
):
    attendance = db.query(Attendance).filter(
        Attendance.booking_id == booking_id
    ).first()

    if not attendance:
        return []

    return (
        db.query(AttendanceHistory)
        .filter(
            AttendanceHistory.attendance_id == attendance.id
        )
        .order_by(
            AttendanceHistory.changed_at.asc()
        )
        .all()
    )
