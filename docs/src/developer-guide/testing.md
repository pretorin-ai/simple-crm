# Testing

## Backend Tests

### Running Tests

```bash
cd backend
source .venv/bin/activate

# Run all tests
python3 -m pytest

# Run with coverage report
python3 -m pytest --cov=app --cov-report=term-missing

# Run a specific test file
python3 -m pytest tests/test_auth_endpoints.py -v

# Run a specific test
python3 -m pytest tests/test_auth_endpoints.py::test_login_success -v
```

### Coverage

100% backend code coverage is enforced via `--cov-fail-under=100` in CI. All new code must include tests.

### Test Setup

Tests use an in-memory SQLite database configured in `tests/conftest.py`:

- Database tables are created before each test and dropped after.
- FastAPI's dependency injection is overridden to use the test database.
- Fixtures provide pre-created users, tokens, and sample data.

### Key Fixtures (`conftest.py`)

| Fixture | Description |
|---------|-------------|
| `client` | FastAPI `TestClient` |
| `db` | SQLAlchemy test session |
| `admin_user` | Admin user record |
| `regular_user` | Regular user record |
| `inactive_user` | Inactive user record |
| `admin_token` / `user_token` | JWT tokens |
| `admin_headers` / `user_headers` | Auth headers dict |
| `sample_contact` | Contact assigned to admin |
| `sample_contract` | Contract record |
| `user_with_api_key` | User with API key (returns tuple) |

### Mocking Patterns

External services are mocked in tests:

```python
# Mock Google ID token verification
@patch("app.auth.GOOGLE_CLIENT_ID", "test-client-id")
@patch("app.auth.google_id_token.verify_oauth2_token")
def test_google_login(mock_verify, client):
    mock_verify.return_value = {"sub": "123", "email": "user@example.com", ...}
    response = client.post("/auth/google", json={"credential": "token"})
    assert response.status_code == 200

# Mock email sending
@patch("app.routers.auth.send_password_reset_email", new_callable=AsyncMock)
def test_password_reset(mock_email, client, admin_user):
    ...

# Mock Gmail API
@patch("app.services.gmail_service.build")
def test_gmail_sync(mock_build, ...):
    ...
```

### Time-Dependent Tests

Use `freezegun` for tests involving time (compliance expiry, follow-ups):

```python
from freezegun import freeze_time

@freeze_time("2025-01-15")
def test_expiring_certifications(client, ...):
    ...
```

## Frontend Tests

### Running Tests

```bash
cd frontend

# Run all tests
npm test

# Run in watch mode
npm test -- --watch

# Run with coverage
npm test -- --coverage
```

### Test Framework

- **Vitest** -- Test runner (Jest-compatible).
- **React Testing Library** -- Component testing.
- **jsdom** -- DOM simulation.

### Test Files

Test files are co-located with source files using the `.test.ts` / `.test.tsx` suffix:

- `src/components/ErrorBoundary.test.tsx`
- `src/contexts/AuthContext.test.tsx`
- `src/lib/api.test.ts`
- `src/lib/badges.test.ts`
- `src/pages/Dashboard.test.tsx`
- `src/pages/Login.test.tsx`

### Setup

`src/test/setup.ts` configures the test environment with `@testing-library/jest-dom` matchers.

## CI Pipeline

GitHub Actions (`.github/workflows/ci.yml`) runs on every push:

1. **Backend lint** -- `ruff check app/ tests/`
2. **Backend security** -- `pip-audit` (dependency vulnerabilities), `bandit` (static security analysis, high-confidence findings)
3. **Backend tests** -- SQLite and PostgreSQL, with 100% coverage enforcement
4. **Frontend lint** -- `eslint`
5. **Frontend tests** -- Vitest
6. **Frontend build** -- Verify production build succeeds

Third-party deprecation warnings are filtered in `pyproject.toml` to keep test output clean.
