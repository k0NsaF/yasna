
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Lesson, Booking, Child
from ..schemas import LessonCreate, LessonResponse, LessonPublicResponse
from ..security import get_current_master, get_current_family

router = APIRouter(tags=["Занятия"])


def lesson_with_places(lesson: Lesson, db: Session):
    """Добавляет к занятию количество записанных детей и свободных мест."""
    booked_count = (
        db.query(Booking)
        .filter(
            Booking.lesson_id == lesson.id,
            Booking.status == "booked",
        )
        .count()
    )

    return {
        "id": lesson.id,
        "title": lesson.title,
        "description": lesson.description,
        "starts_at": lesson.starts_at,
        "duration_minutes": lesson.duration_minutes,
        "capacity": lesson.capacity,
        "price": lesson.price,
        "is_active": lesson.is_active,
        "created_at": lesson.created_at,
        "booked_count": booked_count,
        "free_places": max(lesson.capacity - booked_count, 0),
    }


# ==========================================
# МАСТЕР: СОЗДАНИЕ ЗАНЯТИЯ
# ==========================================

@router.post(
    "/api/master/lessons",
    response_model=LessonResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_lesson(
    data: LessonCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(get_current_master),
):
    lesson = Lesson(
        title=data.title,
        description=data.description,
        starts_at=data.starts_at,
        duration_minutes=data.duration_minutes,
        capacity=data.capacity,
        price=data.price,
        is_active=True,
    )

    db.add(lesson)
    db.commit()
    db.refresh(lesson)

    return lesson


# ==========================================
# МАСТЕР: ПРОСМОТР ВСЕХ ЗАНЯТИЙ
# ==========================================

@router.get(
    "/api/master/lessons",
    response_model=list[LessonPublicResponse],
)
def master_lessons(
    db: Session = Depends(get_db),
    _: bool = Depends(get_current_master),
):
    lessons = (
        db.query(Lesson)
        .order_by(Lesson.starts_at)
        .all()
    )

    return [
        lesson_with_places(lesson, db)
        for lesson in lessons
    ]


# ==========================================
# МАСТЕР: ДЕТИ, ЗАПИСАННЫЕ НА ЗАНЯТИЕ
# ==========================================

@router.get("/api/master/lessons/{lesson_id}/bookings")
def lesson_bookings(
    lesson_id: int,
    db: Session = Depends(get_db),
    master=Depends(get_current_master),
):
    records = (
        db.query(Booking, Child)
        .join(Child, Booking.child_id == Child.id)
        .filter(
            Booking.lesson_id == lesson_id,
            Booking.status == "booked",
        )
        .order_by(Child.first_name)
        .all()
    )

    result = []

    for booking, child in records:
        child_name = " ".join(
            part
            for part in [child.first_name, child.last_name]
            if part
        )

        result.append({
            "booking_id": booking.id,
            "child_name": child_name,
        })

    return result


# ==========================================
# ПУБЛИЧНОЕ РАСПИСАНИЕ
# Авторизация не требуется
# ==========================================

@router.get(
    "/api/lessons",
    response_model=list[LessonPublicResponse],
)
def public_lessons(
    db: Session = Depends(get_db),
):
    lessons = (
        db.query(Lesson)
        .filter(Lesson.is_active.is_(True))
        .order_by(Lesson.starts_at)
        .all()
    )

    return [
        lesson_with_places(lesson, db)
        for lesson in lessons
    ]


# ==========================================
# ПРОСМОТР ОДНОГО ЗАНЯТИЯ СЕМЬЁЙ
# ==========================================

@router.get(
    "/api/lessons/{lesson_id}",
    response_model=LessonPublicResponse,
)
def get_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    family=Depends(get_current_family),
):
    lesson = (
        db.query(Lesson)
        .filter(
            Lesson.id == lesson_id,
            Lesson.is_active.is_(True),
        )
        .first()
    )

    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Занятие не найдено",
        )

    return lesson_with_places(lesson, db)
