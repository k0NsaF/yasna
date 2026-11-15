
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Payment
from ..security import get_current_master, get_current_family
from ..schemas import (
    PaymentCreate,
    PaymentResponse,
    PaymentStatusUpdate,
)
from ..services.payment_service import (
    create_payment,
    get_family_payments,
    get_all_payments,
    update_payment_status,
)


router = APIRouter(tags=["Платежи"])


# ---------- РОДИТЕЛИ ----------

@router.post(
    "/api/family/payments",
    response_model=PaymentResponse,
)
def family_create_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    family=Depends(get_current_family),
):
    if payload.family_id != family.id:
        raise HTTPException(
            status_code=403,
            detail="Нельзя создать платёж для другой семьи",
        )

    return create_payment(
        db=db,
        family_id=family.id,
        subscription_id=payload.subscription_id,
        booking_id=payload.booking_id,
        amount=payload.amount,
        payment_method=payload.payment_method,
    )


@router.get(
    "/api/family/payments",
    response_model=list[PaymentResponse],
)
def family_payments(
    db: Session = Depends(get_db),
    family=Depends(get_current_family),
):
    return get_family_payments(db, family.id)


# Демонстрационное подтверждение оплаты родителем.
@router.post(
    "/api/family/payments/{payment_id}/simulate",
    response_model=PaymentResponse,
)
def family_simulate_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    family=Depends(get_current_family),
):
    payment = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.family_id == family.id,
    ).first()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Платёж не найден",
        )

    return update_payment_status(
        db=db,
        payment_id=payment_id,
        new_status="succeeded",
    )


# ---------- МАСТЕР ----------

@router.get(
    "/api/master/payments",
    response_model=list[PaymentResponse],
)
def master_payments(
    db: Session = Depends(get_db),
    master=Depends(get_current_master),
):
    return get_all_payments(db)


@router.patch(
    "/api/master/payments/{payment_id}/status",
    response_model=PaymentResponse,
)
def master_update_payment(
    payment_id: int,
    payload: PaymentStatusUpdate,
    db: Session = Depends(get_db),
    master=Depends(get_current_master),
):
    return update_payment_status(
        db=db,
        payment_id=payment_id,
        new_status=payload.status,
    )
