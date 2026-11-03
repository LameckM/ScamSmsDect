"""
Trains a scam-message classifier from moderator-confirmed labels already
sitting in your database — no separate labeling step needed.

Every report against an "escalated" number is a confirmed scam example.
Every report against a "cleared" number is a confirmed not-scam example.
"flagged" and "monitoring" numbers are excluded, since those haven't been
confirmed by a human yet.

Run whenever you want to (re)train, from your project root (the folder
containing `app/`, not inside it):

    python scripts/train_model.py

This is a standalone script, not part of the live API — the trained model
is saved to app/ml/model.pkl and would be loaded separately by the scoring
engine (a follow-up step, not wired in yet). A retrain never risks breaking
the running API mid-request.

Design notes, matching what was discussed before writing this:

- Two vectorizers, not one. Word n-grams catch scam phrasing generally.
  Character n-grams catch deliberate evasion — "P1N" instead of "PIN",
  extra spacing inserted to dodge exact-word matching — which word-level
  matching alone misses.
- MIN_EXAMPLES_PER_CLASS is a hard gate, not a suggestion. Training on too
  few examples doesn't produce a model that generalizes — it produces a
  model that memorizes the specific words in those few messages, which
  fails on new phrasing for the same underlying reason the keyword system
  fails on messages it has no keyword for. Refusing to train below this
  threshold is the concrete version of that concern, not just a comment.
- The top-weighted-terms printout at the end IS the "which words is this
  actually learning" answer — inspect it before trusting the model, and
  feed anything that looks like a real pattern back into ScamPattern.
"""

from __future__ import annotations

import pickle
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# So `from app import models` resolves regardless of where this script is
# invoked from, as long as it's still sitting in scripts/ under the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from backend import models
from backend.database import SessionLocal

MIN_EXAMPLES_PER_CLASS = 10
MIN_EXAMPLES_FOR_TEST_SPLIT = 40  # below this, train on everything instead
TOP_N_TERMS = 20
MODEL_PATH = Path(__file__).resolve().parent.parent / "app" / "ml" / "model.pkl"


def load_labeled_examples(db):
    """Returns (texts, labels): label 1 = confirmed scam (escalated),
    label 0 = confirmed not-scam (cleared)."""
    escalated = (
        db.query(models.Report.message_content)
        .join(models.PhoneNumber)
        .filter(models.PhoneNumber.status == "escalated")
        .all()
    )
    cleared = (
        db.query(models.Report.message_content)
        .join(models.PhoneNumber)
        .filter(models.PhoneNumber.status == "cleared")
        .all()
    )
    texts = [row[0] for row in escalated] + [row[0] for row in cleared]
    labels = [1] * len(escalated) + [0] * len(cleared)
    return texts, labels


def vectorize(texts, word_vectorizer, char_vectorizer, fit: bool):
    """Fits (or just applies, if fit=False) both vectorizers on the same
    raw text and concatenates the results into one feature matrix. Word
    features always come first — top_weighted_terms() below relies on
    that ordering to slice out just the word-level weights afterward."""
    if fit:
        word_features = word_vectorizer.fit_transform(texts)
        char_features = char_vectorizer.fit_transform(texts)
    else:
        word_features = word_vectorizer.transform(texts)
        char_features = char_vectorizer.transform(texts)
    return hstack([word_features, char_features]).tocsr()


def top_weighted_terms(word_vectorizer, coefficients, n=TOP_N_TERMS):
    """The classifier's learned weights on the word-level features ARE the
    'most used scam words' discovery — this just sorts and labels them."""
    feature_names = word_vectorizer.get_feature_names_out()
    word_weight_count = len(feature_names)
    word_weights = coefficients[:word_weight_count]

    ranked = sorted(zip(feature_names, word_weights), key=lambda pair: pair[1])
    most_legitimate = ranked[:n]
    most_scammy = list(reversed(ranked[-n:]))
    return most_scammy, most_legitimate


def main():
    db = SessionLocal()
    try:
        texts, labels = load_labeled_examples(db)
    finally:
        db.close()

    counts = Counter(labels)
    n_scam = counts.get(1, 0)
    n_clean = counts.get(0, 0)

    print(f"Confirmed scam examples (escalated):      {n_scam}")
    print(f"Confirmed legitimate examples (cleared):  {n_clean}")
    print()

    if n_scam < MIN_EXAMPLES_PER_CLASS or n_clean < MIN_EXAMPLES_PER_CLASS:
        print(
            f"Not enough confirmed labels yet to train safely — need at least "
            f"{MIN_EXAMPLES_PER_CLASS} of each (escalated AND cleared).\n\n"
            f"With this little data the model would memorize the specific words "
            f"in these few messages rather than learning general scam patterns — "
            f"the overfitting risk flagged when this was first planned. Go "
            f"confirm/dismiss more numbers on the moderation dashboard, then "
            f"re-run this script."
        )
        return

    total = n_scam + n_clean
    use_test_split = total >= MIN_EXAMPLES_FOR_TEST_SPLIT

    if use_test_split:
        train_texts, test_texts, y_train, y_test = train_test_split(
            texts, labels, test_size=0.25, random_state=42, stratify=labels
        )
    else:
        train_texts, y_train = texts, labels
        test_texts, y_test = None, None
        print(
            f"Only {total} examples total — training on all of them and skipping "
            f"a held-out test split (too little data to carve out a meaningful "
            f"test set on top of training). Treat this run as provisional; once "
            f"you're past {MIN_EXAMPLES_FOR_TEST_SPLIT} total examples this script "
            f"will start reporting real held-out accuracy instead.\n"
        )

    word_vectorizer = TfidfVectorizer(
        analyzer="word", ngram_range=(1, 2), min_df=2, max_features=3000, sublinear_tf=True
    )
    char_vectorizer = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(3, 5), min_df=2, max_features=3000, sublinear_tf=True
    )

    X_train = vectorize(train_texts, word_vectorizer, char_vectorizer, fit=True)
    classifier = LogisticRegression(max_iter=1000, class_weight="balanced")
    classifier.fit(X_train, y_train)

    if test_texts is not None:
        X_test = vectorize(test_texts, word_vectorizer, char_vectorizer, fit=False)
        predictions = classifier.predict(X_test)
        print("Held-out test performance:")
        print(classification_report(y_test, predictions, target_names=["not scam", "scam"]))
        print("Confusion matrix (rows = actual, cols = predicted; order: not scam, scam):")
        print(confusion_matrix(y_test, predictions))
        print()

    most_scammy, most_legitimate = top_weighted_terms(word_vectorizer, classifier.coef_[0])

    print(f"Top {TOP_N_TERMS} terms pushing toward 'scam':")
    for term, weight in most_scammy:
        print(f"  {term:30s} {weight:+.3f}")
    print()
    print(f"Top {TOP_N_TERMS} terms pushing toward 'legitimate':")
    for term, weight in most_legitimate:
        print(f"  {term:30s} {weight:+.3f}")
    print()

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(
            {
                "word_vectorizer": word_vectorizer,
                "char_vectorizer": char_vectorizer,
                "classifier": classifier,
                "trained_at": datetime.now(timezone.utc).isoformat(),
                "n_scam_examples": n_scam,
                "n_clean_examples": n_clean,
                "used_test_split": use_test_split,
            },
            f,
        )
    print(f"Model saved to {MODEL_PATH}")
    print(
        "\nThis model isn't wired into the live scoring engine yet — that's a "
        "separate step (loading it in app/scoring.py as one more signal "
        "alongside the existing keyword flags, never replacing them)."
    )


if __name__ == "__main__":
    main()
