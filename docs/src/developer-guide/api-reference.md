# API Reference

The backend provides a full REST API. Interactive documentation is available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## Authentication

All endpoints (except login, password reset, and health check) require authentication:

```
Authorization: Bearer <jwt_token_or_api_key>
```

## Endpoints Summary

### Auth (`/auth`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/auth/login` | Email/password login | None |
| POST | `/auth/google` | Google ID token login | None |
| POST | `/auth/register` | Create user | Admin |
| GET | `/auth/me` | Get current user | JWT/API key |
| POST | `/auth/password-reset-request` | Request password reset | None |
| POST | `/auth/password-reset` | Reset password with token | None |
| POST | `/auth/refresh` | Refresh access token | None (refresh token) |
| POST | `/auth/password-change` | Change password | JWT |

### Users (`/users`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/users` | List all users | Admin |
| POST | `/users` | Create user | Admin |
| GET | `/users/{id}` | Get user | Admin |
| PUT | `/users/{id}` | Update user | Admin |
| DELETE | `/users/{id}` | Delete user | Admin |
| GET | `/users/me/api-key/status` | Check API key status | JWT |
| POST | `/users/me/api-key/generate` | Generate API key | JWT |
| DELETE | `/users/me/api-key` | Revoke API key | JWT |

### Accounts (`/accounts`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/accounts` | List accounts (optional `?account_type=` filter) | JWT |
| POST | `/accounts` | Create account | JWT |
| GET | `/accounts/{id}` | Get account | JWT |
| PUT | `/accounts/{id}` | Update account | JWT (creator/admin) |
| PATCH | `/accounts/{id}` | Partial update | JWT (creator/admin) |
| DELETE | `/accounts/{id}` | Delete account | JWT (creator/admin) |

### Contacts (`/contacts`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/contacts` | List contacts | JWT |
| POST | `/contacts` | Create contact | JWT |
| GET | `/contacts/{id}` | Get contact | JWT |
| PUT | `/contacts/{id}` | Update contact | JWT |
| PATCH | `/contacts/{id}` | Partial update | JWT |
| DELETE | `/contacts/{id}` | Delete contact | JWT |
| GET | `/contacts/follow-ups/due` | Due follow-ups (`?days_ahead=7`) | JWT |
| GET | `/contacts/follow-ups/overdue` | Overdue follow-ups | JWT |

### Communications (`/communications`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/communications` | List (optional `?contact_id=`) | JWT |
| POST | `/communications` | Log communication | JWT |
| DELETE | `/communications/{id}` | Delete communication | JWT |

### Opportunities (`/opportunities`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/opportunities` | List with filters | JWT |
| POST | `/opportunities` | Create opportunity | JWT |
| GET | `/opportunities/pipeline` | Pipeline metrics | JWT |
| GET | `/opportunities/{id}` | Get opportunity | JWT |
| PUT | `/opportunities/{id}` | Update opportunity | JWT |
| PATCH | `/opportunities/{id}` | Partial update | JWT |
| DELETE | `/opportunities/{id}` | Soft delete | JWT |
| POST | `/opportunities/{id}/restore` | Restore deleted | Admin |

### Timeline (`/opportunities/{id}/timeline`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/opportunities/{id}/timeline` | List events | JWT |
| POST | `/opportunities/{id}/timeline` | Create event | JWT |
| DELETE | `/opportunities/{id}/timeline/{event_id}` | Delete event | JWT |

### Capture Notes (`/opportunities/{id}/capture-notes`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/opportunities/{id}/capture-notes` | List sections | JWT |
| PUT | `/opportunities/{id}/capture-notes/{section}` | Upsert section | JWT |

### Attachments (`/opportunities/{id}/attachments`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/opportunities/{id}/attachments` | List attachments | JWT |
| POST | `/opportunities/{id}/attachments` | Upload file (multipart) | JWT |
| GET | `/opportunities/{id}/attachments/{att_id}/download` | Download file | JWT |
| DELETE | `/opportunities/{id}/attachments/{att_id}` | Delete attachment | JWT |

### Contract Vehicles (`/vehicles`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/vehicles` | List vehicles | JWT |
| POST | `/vehicles` | Create vehicle | JWT |
| GET | `/vehicles/{id}` | Get vehicle | JWT |
| PUT | `/vehicles/{id}` | Update vehicle | JWT (creator/admin) |
| DELETE | `/vehicles/{id}` | Delete vehicle | JWT (creator/admin) |

### Teaming (`/teaming`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/teaming` | List (optional `?opportunity_id=`) | JWT |
| POST | `/teaming` | Create teaming record | JWT |
| PATCH | `/teaming/{id}` | Update teaming | JWT (creator/admin) |
| DELETE | `/teaming/{id}` | Delete teaming | JWT (creator/admin) |

### Proposals (`/proposals`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/proposals` | List (optional `?opportunity_id=`) | JWT |
| POST | `/proposals` | Create proposal | JWT |
| PATCH | `/proposals/{id}` | Update proposal | JWT (creator/admin) |
| DELETE | `/proposals/{id}` | Delete proposal | JWT (creator/admin) |

### Compliance (`/compliance`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/compliance` | List certifications | JWT |
| POST | `/compliance` | Create certification | JWT |
| GET | `/compliance/expiring` | Expiring certs (`?days_ahead=90`) | JWT |
| PUT | `/compliance/{id}` | Update certification | JWT (creator/admin) |
| DELETE | `/compliance/{id}` | Delete certification | JWT (creator/admin) |

### Gmail (`/gmail`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/gmail/status` | Connection status | JWT |
| GET | `/gmail/auth-url` | Get OAuth authorization URL | JWT |
| GET | `/gmail/callback` | OAuth callback (browser redirect) | None |
| DELETE | `/gmail/disconnect` | Disconnect Gmail | JWT |
| POST | `/gmail/webhook` | Pub/Sub push notification | None |
| POST | `/gmail/send` | Send email | JWT |

### Contracts (`/contracts`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/contracts` | List contracts | JWT |
| POST | `/contracts` | Create contract | JWT |
| GET | `/contracts/{id}` | Get contract | JWT |
| PUT | `/contracts/{id}` | Update contract | JWT |
| PATCH | `/contracts/{id}` | Partial update | JWT |
| DELETE | `/contracts/{id}` | Delete contract | JWT |
| POST | `/contracts/import` | Import from SAM.gov | JWT |

### Other

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/` | API info | None |
| GET | `/health` | Health check | None |
| GET | `/audit-log` | Audit log | Admin |
| POST | `/sam-gov/collect` | Scrape SAM.gov | JWT |
