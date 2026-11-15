from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..security import get_current_master
from ..schemas import AttendanceUpdate, AttendanceResponse
from ..models import Booking, Child, Lesson, Attendance
from ..services.attendance_service import (
    mark_attendance,
    get_attendance_history,
)

router = APIRouter(
    prefix="/api/master",
    tags=["Посещаемость"],
)


@router.get("/attendance")
def get_attendance_list(
    db: Session = Depends(get_db),
    master=Depends(get_current_master),
):
    records = (
        db.query(Booking, Child, Lesson, Attendance)
        .join(Child, Booking.child_id == Child.id)
        .join(Lesson, Booking.lesson_id == Lesson.id)
        .outerjoin(Attendance, Attendance.booking_id == Booking.id)
        .filter(Booking.status == "booked")
        .order_by(Lesson.starts_at, Child.first_name)
        .all()
    )

    result = []

    for booking, child, lesson, attendance in records:
        child_name = " ".join(
            part for part in [child.first_name, child.last_name] if part
        )

        result.append({
            "id": booking.id,
            "childName": child_name,
            "lessonTitle": lesson.title,
            "status": attendance.status if attendance else "pending",
        })

    return result


@router.put(
    "/bookings/{booking_id}/attendance",
    response_model=AttendanceResponse,
)
def update_attendance(
    booking_id: int,
    payload: AttendanceUpdate,
    db: Session = Depends(get_db),
    master=Depends(get_current_master),
):
    return mark_attendance(
        db=db,
        booking_id=booking_id,
        new_status=payload.status,
        comment=getattr(payload, "comment", None),
    )


@router.get("/bookings/{booking_id}/attendance/history")
def attendance_history(
    booking_id: int,
    db: Session = Depends(get_db),
    master=Depends(get_current_master),
):
    return get_attendance_history(db, booking_id)
