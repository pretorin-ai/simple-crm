# Google Authentication Setup

Pretorin CRM supports Google Sign-In, allowing users to authenticate with their Google accounts.

## Overview

The Google Sign-In flow works as follows:

1. User clicks "Sign in with Google" on the login page.
2. Google displays a consent popup.
3. User selects their Google account.
4. Google returns an ID token to the frontend.
5. The frontend sends the ID token to the backend for verification.
6. The backend verifies the token with Google, finds or creates the user, and returns a CRM JWT.

## Setup Steps

### 1. Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Enable the necessary APIs (if also using Gmail, enable the Gmail API).

### 2. Create OAuth2 Credentials

1. Navigate to **APIs & Services > Credentials**.
2. Click **Create Credentials > OAuth client ID**.
3. Select **Web application** as the application type.
4. Configure the credential:
   - **Name**: "Pretorin CRM" (or your preferred name)
   - **Authorized JavaScript origins**: Add your frontend URL(s):
     - Development: `http://localhost:5173`
     - Production: `https://your-domain.com`
   - **Authorized redirect URIs**: Add your backend callback URL:
     - Development: `http://localhost:8000/gmail/callback`
     - Production: `https://api.your-domain.com/gmail/callback`
5. Click **Create**.
6. Note the **Client ID** and **Client Secret**.

### 3. Configure the Backend

Set the following in `backend/.env`:

```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

The `GOOGLE_CLIENT_SECRET` is only needed for Gmail integration, not for Google Sign-In.

### 4. Configure the Client ID

Set `GOOGLE_CLIENT_ID` in your root `.env`. It is shared with both the backend and frontend automatically:

```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

### 5. Configure the OAuth Consent Screen

1. In the Google Cloud Console, go to **APIs & Services > OAuth consent screen**.
2. Set the user type:
   - **Internal** -- Only users in your Google Workspace organization (recommended for enterprise).
   - **External** -- Any Google account (requires Google verification for production).
3. Fill in the required fields (app name, user support email, developer contact).
4. Add scopes: `email`, `profile`, `openid`.
5. Save.

## How It Works

### New Users

When a user signs in with Google and no CRM account exists for their email:
- A new user account is created automatically.
- The role is set to "user" by default.
- An admin can later promote them to "admin" via User Management.

### Existing Users

When a user signs in with Google and a CRM account with their email already exists:
- The Google identity is linked to the existing account.
- The user's existing role and data are preserved.
- They can now sign in with either Google or their password.

### Account Restrictions

- Only Google accounts with verified emails are allowed.
- Inactive CRM accounts cannot sign in, even with a valid Google identity.
- The Google Sign-In button only appears on the login page when `GOOGLE_CLIENT_ID` is configured.

## Visibility

The "Sign in with Google" button on the login page is **only rendered when `GOOGLE_CLIENT_ID` is set**. If the variable is empty or missing, the login page shows only the email/password form with no indication that Google sign-in exists.

`GOOGLE_CLIENT_ID` is set once in the root `.env` and shared with both the backend (for token verification) and frontend (for the Google Identity Services SDK) via docker-compose and the Dockerfile.

## Disabling Google Sign-In

To disable Google Sign-In, remove or leave empty the `GOOGLE_CLIENT_ID` environment variable. The Sign-In button will not appear on the login page, and the backend endpoint will return a 503 error if called directly.
