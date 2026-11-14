
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Child
from ..schemas import FamilyResponse, ChildResponse
from ..security import get_current_family

router = APIRouter(prefix="/api/family", tags=["Родитель"])


@router.get("/me", response_model=FamilyResponse)
def family_me(
    family=Depends(get_current_family),
):
    return family


@router.get("/children", response_model=list[ChildResponse])
def family_children(
    family=Depends(get_current_family),
    db: Session = Depends(get_db),
):
    children = (
        db.query(Child)
        .filter(Child.family_id == family.id)
        .order_by(Child.id)
        .all()
    )
    return children
