
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..security import get_current_family
from ..schemas import BookingCreate, BookingResponse
from ..services.booking_service import create_booking, cancel_booking
from ..models import Booking, Child


router = APIRouter(
    prefix="/api/family",
    tags=["Запись на занятия"],
)


@router.post("/bookings", response_model=BookingResponse)
def book_lesson(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    family=Depends(get_current_family),
):
    return create_booking(
        db=db,
        family_id=family.id,
        child_id=payload.child_id,
        lesson_id=payload.lesson_id,
    )


@router.get("/bookings", response_model=list[BookingResponse])
def get_bookings(
    db: Session = Depends(get_db),
    family=Depends(get_current_family),
):
    return (
        db.query(Booking)
        .join(Child, Booking.child_id == Child.id)
        .filter(Child.family_id == family.id)
        .order_by(Booking.created_at.desc())
        .all()
    )


@router.delete("/bookings/{booking_id}", response_model=BookingResponse)
def delete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    family=Depends(get_current_family),
):
    return cancel_booking(
        db=db,
        family_id=family.id,
        booking_id=booking_id,
    )
