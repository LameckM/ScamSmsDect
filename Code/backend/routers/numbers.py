from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/numbers", tags=["numbers"])


@router.get("", response_model=list[schemas.PhoneNumberOut])
def list_numbers(
    status: str | None = Query(None, description="Filter by status: monitoring | flagged | escalated | cleared"),
    db: Session = Depends(get_db),
):
    """Lists all reported numbers, most recently updated first. This backs
    the moderation dashboard's main table."""
    query = db.query(models.PhoneNumber)
    if status:
        query = query.filter(models.PhoneNumber.status == status)
    numbers = query.order_by(models.PhoneNumber.updated_at.desc()).all()

    return [
        schemas.PhoneNumberOut(
            number=n.number,
            status=n.status,
            aggregate_score=n.aggregate_score,
            report_count=len(n.reports),
            updated_at=n.updated_at,
        )
        for n in numbers
    ]


@router.get("/{number}", response_model=schemas.PhoneNumberDetail)
def get_number(number: str, db: Session = Depends(get_db)):
    """Full detail for one number, including every report against it —
    used when a moderator opens a flagged number to review evidence."""
    phone = db.query(models.PhoneNumber).filter_by(number=number).first()
    if phone is None:
        raise HTTPException(status_code=404, detail="Number not found")

    return schemas.PhoneNumberDetail(
        number=phone.number,
        status=phone.status,
        aggregate_score=phone.aggregate_score,
        report_count=len(phone.reports),
        updated_at=phone.updated_at,
        reports=phone.reports,
    )
