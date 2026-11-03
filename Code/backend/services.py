"""Database helper functions shared across routers. Kept separate from the
routers themselves so that reports.py and moderation.py don't need to import
from one another."""

from sqlalchemy.orm import Session

from . import models, scoring
from .config import settings


def get_or_create_reporter(db: Session, device_id: str) -> models.Reporter:
    reporter = db.query(models.Reporter).filter_by(device_id=device_id).first()
    if reporter is None:
        reporter = models.Reporter(device_id=device_id)
        db.add(reporter)
        db.flush()  # assigns reporter.id without committing yet
    return reporter


def get_or_create_number(db: Session, number: str) -> models.PhoneNumber:
    phone = db.query(models.PhoneNumber).filter_by(number=number).first()
    if phone is None:
        phone = models.PhoneNumber(number=number)
        db.add(phone)
        db.flush()
    return phone


def load_patterns(db: Session) -> dict[str, list[str]]:
    patterns: dict[str, list[str]] = {}
    for row in db.query(models.ScamPattern).all():
        patterns.setdefault(row.category, []).append(row.phrase)
    return patterns or scoring.load_default_patterns()


def load_corpus(db: Session, exclude_number_id: int, limit: int = 200) -> list[str]:
    """Confirmed-scam message text to compare new reports against for
    similarity. Pulled only from numbers that are already flagged or
    escalated — messages the system already has reason to treat as scams,
    not just anything anyone has reported."""
    rows = (
        db.query(models.Report.message_content)
        .join(models.PhoneNumber)
        .filter(models.PhoneNumber.status.in_(["flagged", "escalated"]))
        .filter(models.PhoneNumber.id != exclude_number_id)
        .order_by(models.Report.created_at.desc())
        .limit(limit)
        .all()
    )
    return [row[0] for row in rows]


def recalculate_number(db: Session, phone: models.PhoneNumber) -> tuple[float, int]:
    """Recomputes a number's aggregate score and status from all of its
    reports, and writes the result onto `phone` (caller still needs to
    commit). Returns (aggregate_score, report_count)."""
    weighted = (
        db.query(models.Report.message_score, models.Reporter.trust_score)
        .join(models.Reporter, models.Report.reporter_id == models.Reporter.id)
        .filter(models.Report.phone_number_id == phone.id)
        .all()
    )
    aggregate = scoring.aggregate_score(weighted)
    effective_reports = sum(weight for _, weight in weighted)

    phone.aggregate_score = aggregate
    phone.status = scoring.determine_status(
        effective_reports,
        aggregate,
        phone.manual_override,
        report_threshold=settings.report_threshold,
        score_threshold=settings.score_threshold,
    )
    return aggregate, len(weighted)
