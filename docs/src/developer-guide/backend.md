# Backend

The backend is a FastAPI application structured around routers, models, schemas, and services.

## Entry Point

`backend/app/main.py` sets up the FastAPI application:

- Configures CORS middleware and request ID middleware.
- Registers all routers.
- Seeds demo data on startup (schema managed by Alembic migrations via `entrypoint.sh`).
- Configures rate limiting, structured JSON logging, Prometheus metrics, and Sentry error reporting.
- Registers global exception handlers (rate limit, unhandled errors).

Start with `python run.py` or `uvicorn app.main:app --reload`.

## Routers

Each router handles a specific resource. All are located in `app/routers/`:

| Router | Prefix | Description |
|--------|--------|-------------|
| `auth.py` | `/auth` | Login, register, password reset, Google auth |
| `users.py` | `/users` | User CRUD, API key management |
| `accounts.py` | `/accounts` | Account CRUD |
| `contacts.py` | `/contacts` | Contact CRUD |
| `contacts_followup.py` | `/contacts` | Follow-up specific endpoints |
| `communications.py` | `/communications` | Communication logging |
| `contracts.py` | `/contracts` | Contract CRUD, SAM.gov import |
| `opportunities.py` | `/opportunities` | Opportunity CRUD, pipeline metrics |
| `timeline.py` | `/opportunities/{id}/timeline` | Opportunity events |
| `capture_notes.py` | `/opportunities/{id}/capture-notes` | Capture intelligence sections |
| `attachments.py` | `/opportunities/{id}/attachments` | File uploads |
| `vehicles.py` | `/vehicles` | Contract vehicle CRUD |
| `teaming.py` | `/teaming` | Teaming relationships |
| `proposals.py` | `/proposals` | Proposal management |
| `compliance.py` | `/compliance` | Certification tracking |
| `gmail.py` | `/gmail` | Gmail OAuth, sync, send |
| `sam_gov.py` | `/sam-gov` | SAM.gov API scraping |
| `audit.py` | `/audit-log` | Audit log access |

## Authentication

All routers use dependency injection for authentication:

```python
from app.auth import get_current_active_user

@router.get("/resource")
def get_resource(current_user: User = Depends(get_current_active_user)):
    ...
```

Three auth dependency levels:
- `get_current_active_user` -- Any active authenticated user.
- `get_current_admin_user` -- Admin role required.
- `get_current_user_or_api_key` -- Accepts JWT or API key.

## Services

Business logic that doesn't fit in routers lives in `app/services/`:

- `gmail_service.py` -- Gmail OAuth2 flow, email sync, sending.
- `sam_gov.py` -- SAM.gov API client for opportunity collection.
- `import_service.py` -- Contract/opportunity import logic.

## Schemas

Pydantic v2 models in `app/schemas/schemas.py` handle request validation and response serialization:

- `*Create` -- Request body for creation.
- `*Update` -- Full update (PUT).
- `*Patch` -- Partial update (PATCH).
- Base model -- Response serialization with `model_config = ConfigDict(from_attributes=True)`.

## Error Handling

- Pydantic validation errors return 422 with field-level details.
- Authentication failures return 401 or 403.
- Business logic errors use `HTTPException` with appropriate status codes.
- Rate limit exceeded returns 429.

## Rate Limiting

Rate limiting uses `slowapi` with per-IP tracking. Applied to sensitive endpoints:

| Endpoint | Limit |
|----------|-------|
| `POST /auth/login` | 5/minute |
| `POST /auth/google` | 10/minute |
| `POST /auth/register` | 5/minute |
| `POST /auth/refresh` | 30/minute |
| `POST /auth/password-reset-request` | 3/minute |
| `POST /auth/password-reset` | 5/minute |

## Observability

- **Structured Logging** -- JSON-formatted logs via `python-json-logger` with request ID context for correlation.
- **Prometheus Metrics** -- Exposed at `/metrics` via `prometheus-fastapi-instrumentator`.
- **Sentry** -- Optional error reporting when `SENTRY_DSN` is configured.
- **Request ID** -- Every request gets a unique ID (from `X-Request-ID` header or auto-generated), returned in the response header and included in all log records.
