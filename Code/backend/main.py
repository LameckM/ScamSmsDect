from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .config import settings
from .database import Base, SessionLocal, engine
from .routers import moderation, numbers, reports
from .seed_data import ensure_default_patterns


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist yet, and seed the scam-pattern
    # corpus on first run. Fine for MVP/local dev; a production deployment
    # would use Alembic migrations instead of create_all.
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_default_patterns(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="ScamShield API",
    description="SMS scam detection and SIM flagging system — report intake, risk scoring, and moderation.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports.router)
app.include_router(numbers.router)
app.include_router(moderation.router)


@app.get("/", include_in_schema=False)
def root():
    """Sends anyone hitting the bare API URL in a browser to the interactive
    docs, since there's no UI served at '/' itself."""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
