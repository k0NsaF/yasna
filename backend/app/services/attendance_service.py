
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

    if attendance is None:
        attendance = Attendance(
            booking_id=booking_id,
            status=new_status,
            marked_at=datetime.utcnow(),
        )
        db.add(attendance)
        db.flush()
    else:
        if old_status == new_status:
            return attendance

        history = AttendanceHistory(
            attendance_id=attendance.id,
            old_status=old_status,
            new_status=new_status,
            changed_at=datetime.utcnow(),
            comment=comment,
        )
        db.add(history)

        attendance.status = new_status
        attendance.marked_at = datetime.utcnow()

    # Находим последнюю операцию по этому бронированию.
    last_transaction = (
        db.query(LessonTransaction)
        .filter(LessonTransaction.booking_id == booking_id)
        .order_by(
            LessonTransaction.created_at.desc(),
            LessonTransaction.id.desc(),
        )
        .first()
    )

    # Если ребёнок посетил занятие — списываем одно занятие.
    if new_status == "attended":
        if last_transaction and last_transaction.operation == "use":
            pass

        elif last_transaction and last_transaction.operation == "refund":
            # Повторно отмечаем посещение после отмены отметки.
            subscription = db.query(Subscription).filter(
                Subscription.id == last_transaction.subscription_id
            ).first()

            if subscription:
                subscription.used_lessons += 1

                db.add(LessonTransaction(
                    subscription_id=subscription.id,
                    booking_id=booking_id,
                    amount=1,
                    operation="use",
                    reason="Повторное подтверждение посещения",
                ))

        else:
            # Сначала ищем абонемент конкретного ребёнка,
            # затем общий абонемент семьи.
            child = db.query(Child).filter(
                Child.id == booking.child_id
            ).first()

            subscription = (
                db.query(Subscription)
                .filter(
                    Subscription.family_id == child.family_id,
                    Subscription.is_active.is_(True),
                    Subscription.used_lessons < Subscription.total_lessons,
                    (
                        (Subscription.child_id == child.id)
                        | (Subscription.child_id.is_(None))
                    ),
                )
                .order_by(
                    Subscription.child_id.is_(None).asc(),
                    Subscription.created_at.desc(),
                )
                .first()
            )

            if subscription:
                subscription.used_lessons += 1

                db.add(LessonTransaction(
                    subscription_id=subscription.id,
                    booking_id=booking_id,
                    amount=1,
                    operation="use",
                    reason="Посещение занятия",
                ))

    # Если отметку «посетил» отменили — возвращаем занятие.
    elif old_status == "attended":
        if last_transaction and last_transaction.operation == "use":
            subscription = db.query(Subscription).filter(
                Subscription.id == last_transaction.subscription_id
            ).first()

            if subscription:
                subscription.used_lessons = max(
                    0,
                    subscription.used_lessons - 1,
                )

                db.add(LessonTransaction(
                    subscription_id=subscription.id,
                    booking_id=booking_id,
                    amount=1,
                    operation="refund",
                    reason="Возврат занятия после изменения посещаемости",
                ))

    try:
        db.commit()
        db.refresh(attendance)
        return attendance
    except Exception:
        db.rollback()
        raise


def get_attendance_history(db: Session, booking_id: int):
    attendance = db.query(Attendance).filter(
        Attendance.booking_id == booking_id
    ).first()

    if not attendance:
        return []

    return (
        db.query(AttendanceHistory)
        .filter(AttendanceHistory.attendance_id == attendance.id)
        .order_by(AttendanceHistory.changed_at.asc())
        .all()
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

    if attendance is None:
        attendance = Attendance(
            booking_id=booking_id,
            status=new_status,
            marked_at=datetime.utcnow(),
        )
        db.add(attendance)
        db.flush()
    else:
        if old_status == new_status:
            return attendance

        history = AttendanceHistory(
            attendance_id=attendance.id,
            old_status=old_status,
            new_status=new_status,
            changed_at=datetime.utcnow(),
            comment=comment,
        )
        db.add(history)

        attendance.status = new_status
        attendance.marked_at = datetime.utcnow()

    # Находим последнюю операцию по этому бронированию.
    last_transaction = (
        db.query(LessonTransaction)
        .filter(LessonTransaction.booking_id == booking_id)
        .order_by(
            LessonTransaction.created_at.desc(),
            LessonTransaction.id.desc(),
        )
        .first()
    )

    # Если ребёнок посетил занятие — списываем одно занятие.
    if new_status == "attended":
        if last_transaction and last_transaction.operation == "use":
            pass

        elif last_transaction and last_transaction.operation == "refund":
            # Повторно отмечаем посещение после отмены отметки.
            subscription = db.query(Subscription).filter(
                Subscription.id == last_transaction.subscription_id
            ).first()

            if subscription:
                subscription.used_lessons += 1

                db.add(LessonTransaction(
                    subscription_id=subscription.id,
                    booking_id=booking_id,
                    amount=1,
                    operation="use",
                    reason="Повторное подтверждение посещения",
                ))

        else:
            # Сначала ищем абонемент конкретного ребёнка,
            # затем общий абонемент семьи.
            child = db.query(Child).filter(
                Child.id == booking.child_id
            ).first()

            subscription = (
                db.query(Subscription)
                .filter(
                    Subscription.family_id == child.family_id,
                    Subscription.is_active.is_(True),
                    Subscription.used_lessons < Subscription.total_lessons,
                    (
                        (Subscription.child_id == child.id)
                        | (Subscription.child_id.is_(None))
                    ),
                )
                .order_by(
                    Subscription.child_id.is_(None).asc(),
                    Subscription.created_at.desc(),
                )
                .first()
            )

            if subscription:
                subscription.used_lessons += 1

                db.add(LessonTransaction(
                    subscription_id=subscription.id,
                    booking_id=booking_id,
                    amount=1,
                    operation="use",
                    reason="Посещение занятия",
                ))

    # Если отметку «посетил» отменили — возвращаем занятие.
    elif old_status == "attended":
        if last_transaction and last_transaction.operation == "use":
            subscription = db.query(Subscription).filter(
                Subscription.id == last_transaction.subscription_id
            ).first()

            if subscription:
                subscription.used_lessons = max(
                    0,
                    subscription.used_lessons - 1,
                )

                db.add(LessonTransaction(
                    subscription_id=subscription.id,
                    booking_id=booking_id,
                    amount=1,
                    operation="refund",
                    reason="Возврат занятия после изменения посещаемости",
                ))

    try:
        db.commit()
        db.refresh(attendance)
        return attendance
    except Exception:
        db.rollback()
        raise


def get_attendance_history(db: Session, booking_id: int):
    attendance = db.query(Attendance).filter(
        Attendance.booking_id == booking_id
    ).first()

    if not attendance:
        return []

    return (
        db.query(AttendanceHistory)
        .filter(AttendanceHistory.attendance_id == attendance.id)
        .order_by(AttendanceHistory.changed_at.asc())
        .all()
    )
