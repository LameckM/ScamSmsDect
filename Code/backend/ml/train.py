"""Train a TF-IDF + Logistic Regression baseline from moderator-confirmed reviews.

Run from the repository root:
    python -m backend.ml.train
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
import joblib

from .. import models  # ensures mappings are registered
from ..database import SessionLocal

MODEL_DIR = Path(os.getenv("SCAM_MODEL_DIR", "backend/ml/artifacts"))
MIN_PER_CLASS = int(os.getenv("SCAM_ML_MIN_PER_CLASS", "10"))

def train():
    db = SessionLocal()
    try:
        rows = db.query(models.ReportReview.label, models.Report.message_content).join(
            models.Report, models.Report.id == models.ReportReview.report_id
        ).filter(models.ReportReview.label.in_(["scam", "legitimate"])).all()
        # Collapse exact duplicate texts to reduce leakage and accidental over-weighting.
        examples = {}
        for label, message in rows:
            normalized = " ".join((message or "").lower().split())
            if len(normalized) >= 3:
                examples.setdefault(normalized, label)
        texts, labels = [], []
        for message, label in examples.items():
            texts.append(message)
            labels.append(label)
        counts = {name: labels.count(name) for name in ("scam", "legitimate")}
        if min(counts.values()) < MIN_PER_CLASS:
            raise ValueError(f"Need at least {MIN_PER_CLASS} unique examples per class; current counts: {counts}")
        train_x, test_x, train_y, test_y = train_test_split(
            texts, labels, test_size=0.25, random_state=42, stratify=labels
        )
        model = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), analyzer="word", min_df=1, max_features=50000, sublinear_tf=True)),
            ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
        ])
        model.fit(train_x, train_y)
        predicted = model.predict(test_x)
        metrics = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "examples_unique": len(texts), "class_counts": counts,
            "train_count": len(train_x), "test_count": len(test_x),
            "accuracy": accuracy_score(test_y, predicted),
            "scam_precision": precision_score(test_y, predicted, pos_label="scam", zero_division=0),
            "scam_recall": recall_score(test_y, predicted, pos_label="scam", zero_division=0),
            "scam_f1": f1_score(test_y, predicted, pos_label="scam", zero_division=0),
            "confusion_matrix_labels": ["legitimate", "scam"],
            "confusion_matrix": confusion_matrix(test_y, predicted, labels=["legitimate", "scam"]).tolist(),
            "note": "Holdout metrics are preliminary; inspect dataset quality and false positives before deployment."
        }
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=MODEL_DIR, suffix=".joblib", delete=False) as handle:
            temp_model = Path(handle.name)
        with tempfile.NamedTemporaryFile(mode="w", dir=MODEL_DIR, suffix=".json", encoding="utf-8", delete=False) as handle:
            temp_metrics = Path(handle.name)
            json.dump(metrics, handle, indent=2)
        joblib.dump(model, temp_model)
        os.replace(temp_model, MODEL_DIR / "candidate.joblib")
        os.replace(temp_metrics, MODEL_DIR / "candidate_metrics.json")
        print(json.dumps(metrics, indent=2))
        print("Candidate model saved. It is NOT automatically deployed.")
        return metrics
    finally:
        db.close()

if __name__ == "__main__":
    train()
