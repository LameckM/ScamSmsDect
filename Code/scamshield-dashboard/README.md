# ScamShield Moderation Dashboard

React (Vite) frontend for the moderation dashboard described in the project
proposal — the human-in-the-loop screen where a reviewer sees flagged
numbers and confirms or dismisses them before anything is escalated.

Talks to the FastAPI backend (`scamshield-backend`) over HTTP. Run that
first — this app has nothing to show without it.

## Setup

```bash
npm install
cp .env.example .env
```

The default `.env` points at `http://localhost:8000`, which matches the
backend's default `uvicorn app.main:app --reload` address. Only change it if
your backend is running somewhere else.

## Run

```bash
npm run dev
```

Opens at `http://localhost:5173`. The backend's default `CORS_ORIGINS`
already includes this address, so no backend config changes should be
needed for local development.

## Using it

1. **Filter tabs** at the top switch between statuses (Flagged, Escalated,
   Monitoring, Cleared, All). The dashboard opens on **Flagged** by default,
   since that's the moderator's actual queue.
2. Click any row to open the **detail panel**, which shows every reported
   message against that number, its individual risk score, and which
   signals were detected (prize language, urgency, requests for money or
   sensitive info, links, similarity to known scams).
3. To **confirm or dismiss** a flagged number, enter a moderator key in the
   top-right field first — this is the same value as `MODERATOR_API_KEY` in
   the backend's `.env` (defaults to `change-me-dev-key`). Without a key
   entered, the action buttons stay disabled.
4. The list **polls every 8 seconds**, so new reports coming in from the
   reporting layer (app/USSD/web) will surface here without a manual
   refresh.

## Notes on scope

- **Auth is a shared key**, matching the backend's current MVP-scope auth
  (see the backend README). Swapping to JWT + role-based login later means
  replacing the moderator-key input with a real login screen and attaching
  the JWT to requests instead of the `X-Moderator-Key` header — the rest of
  the app doesn't need to change.
- **No build-time API mocking** — this app always talks to a real backend.
  If you want to demo the UI without a backend running, the earlier
  interactive prototype (the chat demo artifact) is a better fit for that.
