# Security

## Authentication

### JWT Tokens

- Tokens are signed with HMAC-SHA256 using the `SECRET_KEY`.
- Access token expiration: 60 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`).
- Refresh token expiration: 7 days (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`).
- Token type field (`"access"` or `"refresh"`) prevents cross-use of token types.
- Tokens are stored in the browser's `localStorage`.

### API Keys

- API keys are prefixed with `crm_` for easy identification.
- Keys are hashed with HMAC-SHA256 before storage -- the raw key is never stored.
- One API key per user.

### Password Security

- Passwords are hashed with bcrypt (direct `bcrypt.hashpw` / `bcrypt.checkpw`).
- Minimum length: 8 characters (enforced by Pydantic schema validation).
- Password reset tokens are hashed before storage and expire after 24 hours.

### Token Encryption

- Gmail OAuth tokens (access and refresh) are encrypted at rest using Fernet symmetric encryption.
- Encryption key is configured via `TOKEN_ENCRYPTION_KEY` environment variable.
- Tokens are encrypted before database storage and decrypted only when needed for API calls.

### Google Sign-In

- Google ID tokens are verified against Google's public keys.
- Only tokens with verified email addresses are accepted.
- The `GOOGLE_CLIENT_ID` audience is validated to prevent token reuse from other applications.

## Rate Limiting

Sensitive endpoints are rate-limited:

| Endpoint | Limit |
|----------|-------|
| `POST /auth/login` | 5 requests/minute |
| `POST /auth/google` | 10 requests/minute |
| `POST /auth/register` | 5 requests/minute |
| `POST /auth/refresh` | 30 requests/minute |
| `POST /auth/password-reset-request` | 3 requests/minute |
| `POST /auth/password-reset` | 5 requests/minute |

## Authorization

- All API endpoints require authentication.
- Users can only modify resources they created (accounts, vehicles, compliance records, teaming, proposals).
- Admin users can modify any resource.
- Admin-only operations: user management, opportunity restore, audit log access.

## File Upload Security

- Uploaded files are stored with randomized filenames to prevent enumeration.
- Path traversal attacks are mitigated with `os.path.realpath()` validation.
- File downloads require authentication.

## CORS

- CORS is restricted to the configured `FRONTEND_URL` and any `EXTRA_CORS_ORIGINS`.
- Only specific HTTP methods and headers are allowed.

## Audit Logging

Sensitive operations are recorded in the audit log:

- Deleting accounts, contacts, opportunities, and contracts.
- Restoring soft-deleted opportunities.

Each audit entry includes the user ID, action, entity type/ID, and timestamp.

## Observability

- **Structured Logging** -- JSON-formatted logs with request ID correlation for tracing requests across log entries.
- **Prometheus Metrics** -- Application metrics exposed at `/metrics` for monitoring and alerting.
- **Sentry Integration** -- Optional error reporting to Sentry when `SENTRY_DSN` is configured.
- **Request ID** -- Every response includes an `X-Request-ID` header for log correlation.

## Database Constraints

- **CHECK constraints** enforce valid enum values at the database level (account types, contact types, statuses, pipeline stages, set-aside types, etc.).
- **Indexes** on frequently queried columns (email, stage, deleted_at, foreign keys) for query performance.

## Infrastructure

- **Graceful Shutdown** -- Backend handles SIGTERM with a 30-second timeout for in-flight requests (`stop_grace_period: 35s` in Docker Compose).
- **Hardened Nginx** -- Frontend nginx configuration includes security headers and restrictive defaults.
- **Resource Limits** -- Docker Compose enforces CPU and memory limits on the backend service.

## Data Backups

A backup script (`scripts/backup.sh`) supports scheduled PostgreSQL backups:

- Automatic Docker or direct `pg_dump` detection.
- Compressed output (gzip).
- Configurable retention period (default: 30 days).
- Cron job installation via `--install-cron` flag.

## Recommendations

1. **Use HTTPS** in production. Configure TLS termination at your load balancer or reverse proxy.
2. **Rotate `SECRET_KEY`** periodically. Note that rotating invalidates all existing JWT tokens and API keys.
3. **Use PostgreSQL** in production. SQLite is not suitable for concurrent access.
4. **Restrict database access** to only the backend service.
5. **Monitor audit logs** for suspicious delete activity.
6. **Set `ENV=production`** to prevent seed data from being loaded.
7. **Configure SMTP** for password reset functionality -- without it, users cannot reset forgotten passwords.
8. **Set `TOKEN_ENCRYPTION_KEY`** for Gmail OAuth token encryption at rest.
9. **Set up backups** -- run `scripts/backup.sh --install-cron` for nightly database backups.
10. **Monitor metrics** -- configure Prometheus scraping of the `/metrics` endpoint for alerting.
