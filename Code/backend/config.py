"""
Application settings, read from environment variables.

Plain dataclass rather than pydantic-settings, so the config module has no
dependency beyond the standard library. Copy .env.example to .env and adjust
before running in anything beyond local development.
"""

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv is a convenience, not a hard requirement — env vars set
    # any other way (shell, Docker, systemd) still work without it.
    pass


@dataclass(frozen=True)
class Settings:
    # Defaults to a local SQLite file so the project runs with zero external
    # setup. Point this at a Postgres URL for anything beyond local dev, e.g.
    # postgresql+psycopg://user:password@localhost:5432/scamshield
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./scamshield.db")

    # Shared-secret auth for moderator-only endpoints (see routers/moderation.py).
    # This is intentionally minimal for MVP scope — the project proposal's
    # production plan calls for JWT auth with reviewer/admin role separation.
    moderator_api_key: str = os.getenv("MODERATOR_API_KEY", "change-me-dev-key")

    # Risk-scoring thresholds, kept configurable per the proposal's point that
    # thresholds should be calibrated against real data rather than fixed.
    report_threshold: float = float(os.getenv("REPORT_THRESHOLD", "3"))
    score_threshold: float = float(os.getenv("SCORE_THRESHOLD", "55"))

    # Comma-separated list of origins allowed to call this API from a browser
    # (the moderation dashboard).
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
