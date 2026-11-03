from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from .. import models, schemas, services
from ..config import settings
from ..database import get_db

router = APIRouter(prefix="/numbers", tags=["moderation"])


def verify_moderator(x_moderator_key: str = Header(..., description="Shared moderator API key")):
    """
    Minimal shared-secret auth, intentionally scoped down for MVP. The
    project proposal's production plan calls for JWT auth with separate
    reviewer/admin roles — this is the placeholder that endpoint would
    replace, kept as a single dependency so that swap only touches one
    function.
    """
    if x_moderator_key != settings.moderator_api_key:
        raise HTTPException(status_code=401, detail="Invalid moderator key")


@router.post(
    "/{number}/moderate",
    response_model=schemas.PhoneNumberOut,
    dependencies=[Depends(verify_moderator)],
)
def moderate_number(number: str, action: schemas.ModerationAction, db: Session = Depends(get_db)):
    """
    The human checkpoint from the system architecture: a moderator confirms
    a flagged number (-> "escalated", ready for the MNO/regulator recommendation
    packet), dismisses it as a false positive (-> "cleared"), or resets it
    back to automatic scoring ("reset").
    """
    phone = db.query(models.PhoneNumber).filter_by(number=number).first()
    if phone is None:
        raise HTTPException(status_code=404, detail="Number not found")

    if action.action == "escalate":
        phone.manual_override = "escalated"
    elif action.action == "clear":
        phone.manual_override = "cleared"
    else:  # "reset"
        phone.manual_override = None

    services.recalculate_number(db, phone)
    db.commit()

    return schemas.PhoneNumberOut(
        number=phone.number,
        status=phone.status,
        aggregate_score=phone.aggregate_score,
        report_count=len(phone.reports),
        updated_at=phone.updated_at,
    )
