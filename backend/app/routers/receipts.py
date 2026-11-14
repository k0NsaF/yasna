
from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..security import get_current_master, get_current_family
from ..models import Payment, Receipt
from ..schemas import ReceiptLinkCreate, ReceiptResponse


router = APIRouter(tags=["Чеки и квитанции"])

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads" / "receipts"
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE = 5 * 1024 * 1024


# ---------- МАСТЕР: ДОБАВИТЬ ССЫЛКУ ----------

@router.post(
    "/api/master/payments/{payment_id}/receipt/link",
    response_model=ReceiptResponse,
)
def add_receipt_link(
    payment_id: int,
    payload: ReceiptLinkCreate,
    db: Session = Depends(get_db),
    master=Depends(get_current_master),
):
    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()

    if not payment:
        raise HTTPException(404, "Платёж не найден")

    if payment.status != "succeeded":
        raise HTTPException(
            400,
            "Чек можно прикрепить только к успешному платежу",
        )

    receipt = Receipt(
        payment_id=payment_id,
        receipt_url=str(payload.receipt_url),
    )

    try:
        db.add(receipt)
        db.commit()
        db.refresh(receipt)
        return receipt
    except Exception:
        db.rollback()
        raise


# ---------- МАСТЕР: ЗАГРУЗИТЬ ФАЙЛ ----------

@router.post(
    "/api/master/payments/{payment_id}/receipt/file",
    response_model=ReceiptResponse,
)
async def upload_receipt_file(
    payment_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    master=Depends(get_current_master),
):
    payment = db.query(Payment).filter(
        Payment.id == payment_id
    ).first()

    if not payment:
        raise HTTPException(404, "Платёж не найден")

    if payment.status != "succeeded":
        raise HTTPException(
            400,
            "Чек можно прикрепить только к успешному платежу",
        )

    extension = Path(file.filename or "").suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            "Разрешены только PDF, PNG, JPG и JPEG",
        )

    content = await file.read(MAX_FILE_SIZE + 1)

    if not content:
        raise HTTPException(400, "Файл пустой")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "Максимальный размер файла — 5 МБ")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}{extension}"
    destination = UPLOAD_DIR / filename

    try:
        destination.write_bytes(content)

        receipt = Receipt(
            payment_id=payment_id,
            file_path=filename,
        )

        db.add(receipt)
        db.commit()
        db.refresh(receipt)

        return receipt

    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise

    finally:
        await file.close()


# ---------- РОДИТЕЛЬ: ПРОСМОТР ЧЕКА ----------

@router.get(
    "/api/family/payments/{payment_id}/receipt",
    response_model=list[ReceiptResponse],
)
def get_family_receipts(
    payment_id: int,
    db: Session = Depends(get_db),
    family=Depends(get_current_family),
):
    payment = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.family_id == family.id,
    ).first()

    if not payment:
        raise HTTPException(404, "Платёж не найден")

    return (
        db.query(Receipt)
        .filter(Receipt.payment_id == payment_id)
        .order_by(Receipt.created_at.desc())
        .all()
    )


# ---------- РОДИТЕЛЬ: СКАЧАТЬ ФАЙЛ ----------

@router.get(
    "/api/family/receipts/{receipt_id}/download"
)
def download_family_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    family=Depends(get_current_family),
):
    receipt = (
        db.query(Receipt)
        .join(Payment, Receipt.payment_id == Payment.id)
        .filter(
            Receipt.id == receipt_id,
            Payment.family_id == family.id,
        )
        .first()
    )

    if not receipt:
        raise HTTPException(404, "Чек не найден")

    if not receipt.file_path:
        raise HTTPException(
            400,
            "Для этого чека доступна ссылка, а не файл",
        )

    file_path = UPLOAD_DIR / Path(receipt.file_path).name

    if not file_path.is_file():
        raise HTTPException(404, "Файл чека не найден на сервере")

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream",
    )
