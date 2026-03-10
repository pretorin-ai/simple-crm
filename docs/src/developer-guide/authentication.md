# Authentication

Pretorin CRM supports three authentication methods: JWT tokens, API keys, and Google Sign-In.

## JWT Authentication

### Login Flow

1. Client sends `POST /auth/login` with email and password.
2. Backend verifies credentials against the bcrypt hash in the database.
3. On success, returns a JWT token signed with `SECRET_KEY` (HS256).
4. Client stores the token in `localStorage` and sends it as `Authorization: Bearer <token>` on subsequent requests.

### Token Structure

```json
{
  "sub": "user@example.com",
  "exp": 1700000000,
  "type": "access"
}
```

The `sub` claim is the user's email. The `type` field distinguishes access tokens from refresh tokens. On each request, the backend decodes the token, looks up the user by email, and checks `is_active`.

### Token Expiration

- **Access tokens**: 60 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`).
- **Refresh tokens**: 7 days (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`).

### Token Refresh

When an access token expires, the client can obtain a new one without re-authenticating:

1. Client sends `POST /auth/refresh` with the refresh token.
2. Backend verifies the token type is "refresh" and the token is valid.
3. Returns a new access token and refresh token pair.

The frontend API client handles this automatically -- on a 401 response, it attempts a refresh and retries the original request. The refresh endpoint is rate-limited to 30 requests/minute.

## API Key Authentication

API keys provide long-lived authentication for programmatic access.

### Format

```
crm_<48 hex characters>
```

Keys are detected by the `crm_` prefix. The backend hashes the key with HMAC-SHA256 and looks up the hash in the database.

### Flow

1. User generates a key via `POST /users/me/api-key/generate`.
2. Raw key is returned once and never stored.
3. The HMAC hash and a display prefix are stored in the user record.
4. Client sends `Authorization: Bearer crm_...` on requests.
5. Backend checks for `crm_` prefix, hashes, and looks up.

## Google Sign-In (IDP)

### Flow

1. Frontend loads the Google Identity Services (GIS) script.
2. User clicks "Sign in with Google" and selects an account.
3. Google returns an ID token (JWT signed by Google).
4. Frontend sends the ID token to `POST /auth/google`.
5. Backend verifies the token using `google.oauth2.id_token.verify_oauth2_token()`.
6. Backend finds or creates the user based on Google's `sub` (unique ID) and `email`.
7. Returns a CRM JWT token for subsequent requests.

### User Resolution

On Google login, the backend:

1. Searches for a user with matching `google_id`.
2. If not found, searches by `email`.
3. If found by email, links the Google identity (`google_id` field).
4. If no user exists, creates a new one with role "user".

### Token Verification

The backend verifies:
- Token signature against Google's public keys.
- Audience matches `GOOGLE_CLIENT_ID`.
- Token is not expired.
- Email is verified by Google (`email_verified: true`).

## Auth Dependencies

`backend/app/auth.py` provides FastAPI dependency functions:

```python
# JWT only -- most endpoints use this
def get_current_active_user(current_user = Depends(get_current_user)):
    ...

# Admin required -- user management, audit log, opportunity restore
def get_current_admin_user(current_user = Depends(get_current_active_user)):
    ...

# JWT or API key -- /auth/me and other flexible endpoints
def get_current_user_or_api_key(credentials = Depends(security)):
    ...
```

## Password Hashing

- Algorithm: bcrypt (direct `bcrypt.hashpw` / `bcrypt.checkpw`).
- Minimum password length: 8 characters.
- Password reset tokens: `secrets.token_urlsafe(32)`, hashed with HMAC-SHA256, 24-hour expiry.

## Security Headers

- CORS restricted to configured origins.
- `Authorization` header required for all protected endpoints.
- Rate limiting on authentication endpoints to prevent brute force.
