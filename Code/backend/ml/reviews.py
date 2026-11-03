"""Moderator review endpoints. Phone-number decisions are not message labels."""
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..routers.moderation import verify_moderator
from .train import train as train_candidate

router = APIRouter(prefix="/review", tags=["message review"])

class ReviewLabel(BaseModel):
    label: Literal["scam", "legitimate"]
    note: str | None = Field(default=None, max_length=1000)

class ReviewOut(BaseModel):
    report_id: int
    message_content: str
    message_score: float
    flags: list[str]
    submitted_at: datetime
    label: str | None = None
    reviewed_at: datetime | None = None

@router.get("/messages", response_model=list[ReviewOut], dependencies=[Depends(verify_moderator)])
def review_queue(status: Literal["pending", "reviewed", "all"] = Query("pending"), limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    query = db.query(models.Report).order_by(models.Report.created_at.desc())
    if status == "pending":
        query = query.outerjoin(models.ReportReview).filter(models.ReportReview.id.is_(None))
    elif status == "reviewed":
        query = query.join(models.ReportReview)
    rows = query.limit(limit).all()
    result = []
    for report in rows:
        review = db.query(models.ReportReview).filter_by(report_id=report.id).first()
        result.append(ReviewOut(report_id=report.id, message_content=report.message_content,
            message_score=report.message_score, flags=report.flags or [], submitted_at=report.created_at,
            label=review.label if review else None, reviewed_at=review.reviewed_at if review else None))
    return result

@router.post("/messages/{report_id}", dependencies=[Depends(verify_moderator)])
def label_message(report_id: int, payload: ReviewLabel, db: Session = Depends(get_db)):
    report = db.query(models.Report).filter_by(id=report_id).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    review = db.query(models.ReportReview).filter_by(report_id=report_id).first()
    if review is None:
        review = models.ReportReview(report_id=report_id, label=payload.label, note=payload.note)
        db.add(review)
    else:
        review.label = payload.label
        review.note = payload.note
        review.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    return {"report_id": report_id, "label": review.label, "reviewed_at": review.reviewed_at, "training_eligible": True}


@router.post("/train", dependencies=[Depends(verify_moderator)])
def train_reviewed_model():
    """Train a candidate from confirmed labels. Candidate is not activated automatically."""
    try:
        metrics = train_candidate()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "candidate_ready", "metrics": metrics, "deployed": False}
