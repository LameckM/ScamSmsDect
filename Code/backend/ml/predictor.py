"""Loads an explicitly activated candidate for optional inference."""
import os
from pathlib import Path
from functools import lru_cache

MODEL_PATH = Path(os.getenv("SCAM_ACTIVE_MODEL_PATH", "backend/ml/artifacts/active.joblib"))

@lru_cache(maxsize=1)
def _load(path_text: str, mtime: float):
    import joblib
    return joblib.load(path_text)

def predict_scam(message: str) -> dict | None:
    """Return scam confidence when active model exists; otherwise None.

    Treat the output as a model score, not a calibrated fraud probability.
    """
    if not MODEL_PATH.is_file():
        return None
    try:
        model = _load(str(MODEL_PATH), MODEL_PATH.stat().st_mtime)
        probs = model.predict_proba([message])[0]
        classes = list(model.classes_)
        if "scam" not in classes:
            return None
        return {"scam_score": float(probs[classes.index("scam")]), "model": "active"}
    except (OSError, ValueError, AttributeError, ImportError):
        # Existing keyword scoring must remain available if model artifact is broken.
        return None
