"""
ScamShield risk-scoring engine.

Deliberately dependency-free (standard library only) so it can be developed,
tested, and reasoned about independently of the web framework and database.
`app/routers/reports.py` is the only place that wires this up to FastAPI/SQLAlchemy.

Two things are scored:
  1. A single message, against known scam-phrase categories and a corpus of
     previously confirmed scam messages (keyword matching + similarity).
  2. A phone number, by aggregating all of its message scores, weighted by
     each reporter's trust score and boosted by how many independent reports
     it has received.

This corresponds to "v1: rule-based keyword matching" from the project
proposal. The `similarity_to_corpus` step is a lightweight stand-in for the
proposal's "v2: embedding-based similarity" — it uses Jaccard similarity over
word sets rather than TF-IDF/embeddings, which keeps it fully offline and
dependency-free. Swapping in scikit-learn (TF-IDF + cosine similarity) or
sentence-transformers later only requires replacing `similarity_to_corpus`;
nothing else in this module needs to change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Points awarded when a message matches at least one phrase in that category.
CATEGORY_WEIGHTS = {
    "lottery": 25,
    "urgency": 20,
    "money": 25,
    "sensitive_info": 25,
}
URL_WEIGHT = 15
SIMILARITY_WEIGHT = 15          # max bonus points from corpus similarity
SIMILARITY_MATCH_THRESHOLD = 0.35  # below this, similarity isn't flagged

URL_PATTERN = re.compile(r"https?://|www\.|bit\.ly|\.com\b|\.net\b", re.IGNORECASE)
TOKEN_PATTERN = re.compile(r"[a-z0-9']+")

FLAG_LABELS = {
    "lottery": "Prize or lottery language",
    "urgency": "Urgency cues",
    "money": "Requests money or payment",
    "sensitive_info": "Requests sensitive info",
    "url": "Contains a link",
}

# Seed vocabulary. In production this is overridden by the ScamPattern table
# (see app/seed_data.py), which lets moderators grow the corpus over time
# without a code change. This dict is the fallback used if that table is
# ever empty, and it's what the standalone tests below run against.
DEFAULT_PATTERNS = {
    "lottery": [
        "congratulations", "you have won", "winner", "lottery", "prize",
        "claim your", "free gift", "cash prize", "jackpot",
    ],
    "urgency": [
        "urgent", "immediately", "expires", "expire", "act now",
        "limited time", "24 hours", "before it expires", "hurry",
    ],
    "money": [
        "send money", "deposit", "transfer fee", "processing fee",
        "mobile money", "western union", "pay now", "send your pin to",
    ],
    "sensitive_info": [
        "pin", "otp", "password", "verify your account", "card number",
        "cvv", "account number", "one time password",
    ],
}

# Report-threshold defaults; overridden by app/config.py in the API layer.
DEFAULT_REPORT_THRESHOLD = 3.0
DEFAULT_SCORE_THRESHOLD = 55.0


def load_default_patterns() -> dict[str, list[str]]:
    """Returns a fresh copy so callers can't mutate the module-level default."""
    return {category: list(phrases) for category, phrases in DEFAULT_PATTERNS.items()}


# ---------------------------------------------------------------------------
# Message-level analysis
# ---------------------------------------------------------------------------

@dataclass
class AnalysisResult:
    score: float
    flags: list[str] = field(default_factory=list)
    similarity: float = 0.0


def _tokenize(text: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(text.lower()))


def similarity_to_corpus(text: str, corpus: list[str]) -> float:
    """
    Jaccard word-overlap similarity between `text` and the closest message
    in `corpus`. Returns 0.0 if the corpus is empty. See module docstring
    for the upgrade path to TF-IDF/embedding similarity.
    """
    if not corpus:
        return 0.0
    tokens = _tokenize(text)
    if not tokens:
        return 0.0
    best = 0.0
    for prior in corpus:
        prior_tokens = _tokenize(prior)
        if not prior_tokens:
            continue
        overlap = len(tokens & prior_tokens) / len(tokens | prior_tokens)
        if overlap > best:
            best = overlap
    return best


def analyze_message(
    text: str,
    patterns: dict[str, list[str]] | None = None,
    corpus: list[str] | None = None,
) -> AnalysisResult:
    """
    Scores a single reported message from 0-100 and returns which risk
    signals were detected.

    `patterns` defaults to DEFAULT_PATTERNS; in the live API it's loaded
    from the ScamPattern table instead (see routers/reports.py).
    `corpus` is the set of previously confirmed scam messages to compare
    against for similarity; pass None or [] to skip that step.
    """
    patterns = patterns or load_default_patterns()
    lower = text.lower()
    flags: list[str] = []
    score = 0

    for category, weight in CATEGORY_WEIGHTS.items():
        phrases = patterns.get(category, [])
        if any(phrase in lower for phrase in phrases):
            flags.append(FLAG_LABELS[category])
            score += weight

    if URL_PATTERN.search(lower):
        flags.append(FLAG_LABELS["url"])
        score += URL_WEIGHT

    similarity = similarity_to_corpus(text, corpus or [])
    if similarity >= SIMILARITY_MATCH_THRESHOLD:
        bonus = round(similarity * SIMILARITY_WEIGHT)
        score += bonus
        flags.append(f"Similar to a previously reported scam ({round(similarity * 100)}% match)")

    return AnalysisResult(score=min(100, score), flags=flags, similarity=similarity)


# ---------------------------------------------------------------------------
# Number-level aggregation
# ---------------------------------------------------------------------------

def aggregate_score(message_scores_with_weights: list[tuple[float, float]]) -> float:
    """
    Combines every message score reported against a number into a single
    aggregate risk score (0-100).

    Each entry is (message_score, reporter_trust_weight). Trust weight lets
    reports from established, reliable reporters count more than reports
    from brand-new or previously-inaccurate ones — this is the system's
    main defense against coordinated false reporting (see proposal, "Abuse
    resistance"). The report-count boost rewards numbers with many
    independent reports, since that itself is a signal, even if no single
    message scores very high.
    """
    total_weight = sum(weight for _, weight in message_scores_with_weights)
    if total_weight <= 0:
        return 0.0
    weighted_avg = sum(score * weight for score, weight in message_scores_with_weights) / total_weight
    boost = 1 + min(total_weight, 8) * 0.04
    return round(min(100.0, weighted_avg * boost), 1)


def determine_status(
    effective_report_count: float,
    aggregate: float,
    manual_override: str | None = None,
    report_threshold: float = DEFAULT_REPORT_THRESHOLD,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
) -> str:
    """
    Decides a number's status. A moderator's manual decision ("escalated" or
    "cleared") always wins and freezes the status until reset, regardless of
    what new reports come in — this is the human-in-the-loop checkpoint from
    the system architecture, and it's what keeps the system advisory rather
    than self-executing.
    """
    if manual_override:
        return manual_override
    if effective_report_count >= report_threshold and aggregate >= score_threshold:
        return "flagged"
    return "monitoring"
