# Contributing

## Development Setup

See the [Installation](../admin-guide/installation.md) guide for setting up the development environment.

## Code Style

### Backend (Python)

- **Linter**: [Ruff](https://docs.astral.sh/ruff/) -- configured in `pyproject.toml`.
- **Line length**: 100 characters.
- **Rules**: E (pycodestyle), F (pyflakes), I (isort), W (warnings).
- **Target**: Python 3.12.

Run the linter:

```bash
cd backend
ruff check app/ tests/
ruff check --fix app/ tests/  # Auto-fix
```

### Frontend (TypeScript)

- **Linter**: ESLint with typescript-eslint.
- **Framework**: React with TypeScript strict mode.

Run the linter:

```bash
cd frontend
npm run lint
```

## Git Workflow

1. Create a feature branch from `main`.
2. Make your changes.
3. Ensure all tests pass and coverage is maintained.
4. Run linters and fix any issues.
5. Commit with a clear message describing the change.
6. Open a pull request against `main`.

## Adding a New Entity

When adding a new data entity, follow this checklist:

### Backend

1. **Model** -- Add SQLAlchemy model in `app/models/models.py`.
2. **Migration** -- Generate an Alembic migration: `alembic revision --autogenerate -m "add entity_name"`.
3. **Schema** -- Add Pydantic schemas in `app/schemas/schemas.py` (Create, Update, Patch, Response).
4. **Router** -- Create a new router in `app/routers/` with CRUD endpoints.
5. **Register** -- Import and include the router in `app/main.py`.
6. **Tests** -- Write tests covering all endpoints with 100% code coverage.
7. **Auth** -- Apply appropriate auth dependencies (`get_current_active_user`, etc.).

### Frontend

1. **API functions** -- Add typed functions in `src/lib/api.ts`.
2. **List page** -- Create a list page in `src/pages/`.
3. **Detail page** -- Create a detail page with edit/delete.
4. **Routes** -- Add routes in `App.tsx` with lazy loading.
5. **Navigation** -- Add sidebar links in `Layout.tsx`.
6. **Badges** -- Add badge helpers in `lib/badges.ts` if the entity has status/type fields.

## Adding a New API Endpoint

1. Add the route handler in the appropriate router file.
2. Define request/response schemas if needed.
3. Apply authentication dependencies.
4. Write tests for success cases, error cases, and authorization.
5. The OpenAPI docs update automatically.

## Pre-Commit Checks

The project includes a pre-commit script in `scripts/`. Before committing:

```bash
# Backend
cd backend
ruff check app/ tests/
python3 -m pytest --cov=app --cov-fail-under=100

# Frontend
cd frontend
npm run lint
npm test
npm run build
```

## Key Patterns to Follow

- **UUIDs**: Use `generate_id()` from `app.utils` for all new record IDs.
- **Auth**: Use `Depends(get_current_active_user)` for standard endpoints, `Depends(get_current_admin_user)` for admin-only.
- **Creator checks**: For mutation endpoints, verify `created_by_user_id == current_user.id or current_user.role == "admin"`.
- **Audit logging**: Log deletions of important entities to the audit log.
- **Pydantic v2**: Use `model_config = ConfigDict(from_attributes=True)` for ORM compatibility.
- **Lazy loading**: Wrap new pages with `React.lazy()` in `App.tsx`.
