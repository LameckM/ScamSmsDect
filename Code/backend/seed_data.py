from sqlalchemy.orm import Session

from . import models
from .scoring import DEFAULT_PATTERNS


def ensure_default_patterns(db: Session) -> None:
    """Populates scam_patterns with the seed vocabulary, but only if empty —
    safe to call on every startup without duplicating rows or clobbering
    phrases a moderator has since added or removed."""
    if db.query(models.ScamPattern).count() > 0:
        return

    for category, phrases in DEFAULT_PATTERNS.items():
        for phrase in phrases:
            db.add(models.ScamPattern(phrase=phrase, category=category))
    db.commit()
