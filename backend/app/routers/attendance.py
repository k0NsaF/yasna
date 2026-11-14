
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..security import get_current_master
from ..schemas import AttendanceUpdate, AttendanceResponse
from ..services.attendance_service import (
    mark_attendance,
    get_attendance_history,
)


router = APIRouter(
    prefix="/api/master",
    tags=["Посещаемость"],
)


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
