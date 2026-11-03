from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas, scoring, services
from ..database import get_db
from ..ml.predictor import predict_scam

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
    ml_result = predict_scam(payload.message)
    message_score = result.score
    flags = list(result.flags)
    if ml_result is not None:
        ml_risk = ml_result['scam_score'] * 100.0
        # Rule score remains dominant; combined score is advisory, not calibrated probability.
        message_score = round(min(100.0, 0.65 * result.score + 0.35 * ml_risk), 1)
        flags.append(f"ML model scam score: {round(ml_risk)} / 100 (advisory)")
        if ml_risk >= 65:
            flags.append("ML model recommends moderator review")

    report = models.Report(
        phone_number_id=phone.id,
        reporter_id=reporter.id,
        message_content=payload.message,
        message_score=message_score,
        flags=flags,
    )
    db.add(report)
    db.flush()

    aggregate, report_count = services.recalculate_number(db, phone)
    db.commit()

    return schemas.ReportResult(
        message_score=message_score,
        flags=flags,
        number=phone.number,
        report_count=report_count,
        aggregate_score=aggregate,
        status=phone.status,
    )
