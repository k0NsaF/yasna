
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Booking, Child, Lesson


def create_booking(
    db: Session,
    family_id: int,
    child_id: int,
    lesson_id: int,
):
    # Проверяем, принадлежит ли ребёнок этой семье.
    child = db.query(Child).filter(
        Child.id == child_id,
        Child.family_id == family_id,
    ).first()

    if not child:
        raise HTTPException(
            status_code=404,
            detail="Ребёнок не найден в вашей семье",
        )

    # Проверяем существование и активность занятия.
    lesson = db.query(Lesson).filter(
        Lesson.id == lesson_id,
        Lesson.is_active.is_(True),
    ).first()

    if not lesson:
        raise HTTPException(
            status_code=404,
            detail="Занятие не найдено или недоступно",
        )

    # Проверяем, что занятие ещё не началось.
    starts_at = lesson.starts_at

    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=timezone.utc)

    if starts_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Нельзя записаться на уже начавшееся занятие",
        )

    # Проверяем существующую запись.
    existing_booking = db.query(Booking).filter(
        Booking.child_id == child_id,
        Booking.lesson_id == lesson_id,
    ).first()

    if existing_booking:
        if existing_booking.status == "booked":
            raise HTTPException(
                status_code=409,
                detail="Ребёнок уже записан на это занятие",
            )

        # Повторно используем отменённую запись.
        existing_booking.status = "booked"
        existing_booking.created_at = datetime.utcnow()
        booking = existing_booking

    else:
        booking = Booking(
            child_id=child_id,
            lesson_id=lesson_id,
            status="booked",
        )
        db.add(booking)

    # Проверяем вместимость занятия.
    booked_count = db.query(Booking).filter(
        Booking.lesson_id == lesson_id,
        Booking.status == "booked",
    ).count()

    if booked_count > lesson.capacity:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Свободных мест на занятии больше нет",
        )

    try:
        db.commit()
        db.refresh(booking)
        return booking
    except Exception:
        db.rollback()
        raise


def cancel_booking(
    db: Session,
    family_id: int,
    booking_id: int,
):
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
            detail="Запись не найдена",
        )

    if booking.status == "cancelled":
        raise HTTPException(
            status_code=409,
            detail="Запись уже отменена",
        )

    lesson = db.query(Lesson).filter(
        Lesson.id == booking.lesson_id
    ).first()

    if not lesson:
        raise HTTPException(
            status_code=404,
            detail="Занятие не найдено",
        )

    starts_at = lesson.starts_at

    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=timezone.utc)

    if starts_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Нельзя отменить запись после начала занятия",
        )

    booking.status = "cancelled"

    try:
        db.commit()
        db.refresh(booking)
        return booking
    except Exception:
        db.rollback()
        raise
