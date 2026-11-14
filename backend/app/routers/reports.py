
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..security import get_current_master
from ..services.export_service import EXPORTS


router = APIRouter(
    prefix="/api/master/reports",
    tags=["Отчёты"]
)


@router.get("/{report_type}/csv")
def download_report(
    report_type: str,
    db: Session = Depends(get_db),
    master=Depends(get_current_master)
):
    export_function = EXPORTS.get(report_type)

    if export_function is None:
        raise HTTPException(
            status_code=404,
            detail="Такой тип отчёта не существует"
        )

    csv_content = export_function(db)

    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{report_type}_report.csv"'
            )
        }
    )
