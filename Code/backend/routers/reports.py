from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas, scoring, services
from ..database import get_db

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=schemas.ReportResult)
def submit_report(payload: schemas.ReportCreate, db: Session = Depends(get_db)):
    """
    Submits a report against a phone number. Creates the reporter and/or
    number records if they're new, scores the message, stores the report,
    then recalculates the number's aggregate risk state.
    """
    reporter = services.get_or_create_reporter(db, payload.device_id)
    phone = services.get_or_create_number(db, payload.number)

    patterns = services.load_patterns(db)
    corpus = services.load_corpus(db, phone.id)
    result = scoring.analyze_message(payload.message, patterns=patterns, corpus=corpus)

    report = models.Report(
        phone_number_id=phone.id,
        reporter_id=reporter.id,
        message_content=payload.message,
        message_score=result.score,
        flags=result.flags,
    )
    db.add(report)
    db.flush()

    aggregate, report_count = services.recalculate_number(db, phone)
    db.commit()

    return schemas.ReportResult(
        message_score=result.score,
        flags=result.flags,
        number=phone.number,
        report_count=report_count,
        aggregate_score=aggregate,
        status=phone.status,
    )
