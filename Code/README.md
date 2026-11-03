# ScamShield Backend

FastAPI backend for the ScamShield SMS scam detection and SIM flagging system.
Implements the "Processing Layer" and "Data Layer" from the project proposal:
report intake, keyword + similarity risk scoring, aggregate risk state per
number, and a moderation endpoint for the human-in-the-loop review step.

## Project structure

```
app/
  main.py         FastAPI app, router registration, startup seeding
  config.py       Settings read from environment variables
  database.py     SQLAlchemy engine/session (SQLite by default, Postgres via DATABASE_URL)
  models.py       ORM models: Reporter, PhoneNumber, Report, ScamPattern
  schemas.py      Pydantic request/response models
  scoring.py      Risk-scoring engine — pure Python, no framework dependency
  seed_data.py    Seeds the scam-pattern corpus on first run
  services.py     Shared DB helpers used by more than one router
  routers/
    reports.py     POST /reports — submit a report
    numbers.py     GET /numbers, GET /numbers/{number} — list & inspect
    moderation.py  POST /numbers/{number}/moderate — moderator review
tests/
  test_scoring.py  Unit tests for the scoring engine (stdlib only, no install needed)
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # adjust MODERATOR_API_KEY at minimum
```

## Run

```bash
uvicorn app.main:app --reload
```

The API is now at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`. A `scamshield.db` SQLite file is created
automatically on first run, along with the seeded scam-pattern corpus.

## Switching to PostgreSQL

Install the driver and point `DATABASE_URL` at your Postgres instance:

```bash
pip install "psycopg[binary]"
```

```
DATABASE_URL=postgresql+psycopg://scamshield:password@localhost:5432/scamshield
```

No code changes needed — `app/database.py` reads the URL and configures
itself accordingly. For schema migrations beyond the initial `create_all`,
introduce Alembic before this goes into production use.

## Running the tests

The scoring engine has no framework dependency, so its tests run with
nothing but the standard library:

```bash
python3 -m unittest discover -s tests -v
```

## Example usage

**Submit a report:**

```bash
curl -X POST http://localhost:8000/reports \
  -H "Content-Type: application/json" \
  -d '{
        "device_id": "device-abc123",
        "number": "+260971234567",
        "message": "Congratulations! You have won K5,000. Send your PIN to claim your prize within 24 hours."
      }'
```

Submit it a few more times (varying wording slightly, same number) to watch
`report_count` and `aggregate_score` climb until `status` flips from
`"monitoring"` to `"flagged"`.

**List flagged numbers (moderation dashboard's main view):**

```bash
curl http://localhost:8000/numbers?status=flagged
```

**Inspect one number's full report history:**

```bash
curl http://localhost:8000/numbers/+260971234567
```

**Moderator confirms a flag** (escalates it, as if recommending the number
to the MNO/regulator):

```bash
curl -X POST http://localhost:8000/numbers/+260971234567/moderate \
  -H "Content-Type: application/json" \
  -H "X-Moderator-Key: change-me-dev-key" \
  -d '{"action": "escalate"}'
```

## What's intentionally out of scope here

Per the project proposal, these are documented as the production path but
not built into this MVP:

- **JWT auth with reviewer/admin roles** — currently a single shared
  moderator API key (see `app/routers/moderation.py`).
- **TF-IDF or embedding-based similarity** — `scoring.similarity_to_corpus`
  currently uses Jaccard word-overlap, which needs no external ML
  dependency. Swapping in `scikit-learn` or `sentence-transformers` only
  requires replacing that one function.
- **Alembic migrations** — tables are created with `Base.metadata.create_all`,
  fine for development but not for evolving a production schema safely.
- **Rate limiting / abuse throttling** on the reporting endpoint itself.
