# Gmail Integration Setup

The Gmail integration allows users to sync their Gmail emails with CRM contacts and send emails directly from the CRM.

## Prerequisites

- A Google Cloud project with OAuth2 credentials (see [Google Authentication Setup](./google-auth-setup.md) for creating the project).
- Gmail API enabled in the project.

## Setup Steps

### 1. Enable the Gmail API

1. In the Google Cloud Console, go to **APIs & Services > Library**.
2. Search for "Gmail API".
3. Click **Enable**.

### 2. Configure OAuth2 Credentials

The same OAuth2 client ID used for Google Sign-In can be reused for Gmail. Ensure the authorized redirect URIs include the Gmail callback:

- Development: `http://localhost:8000/gmail/callback`
- Production: `https://api.your-domain.com/gmail/callback`

### 3. Set Environment Variables

In `backend/.env`:

```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/gmail/callback
```

### 4. (Optional) Configure Pub/Sub for Real-Time Sync

For real-time email sync via push notifications:

1. Enable the **Cloud Pub/Sub API** in your Google Cloud project.
2. Create a Pub/Sub topic.
3. Grant the Gmail API service account (`gmail-api-push@system.gserviceaccount.com`) publish permission on the topic.
4. Set the topic in `.env`:

```
GOOGLE_PUBSUB_TOPIC=projects/your-project/topics/gmail-push
```

5. Set a shared webhook token for request verification:

```
GMAIL_WEBHOOK_TOKEN=your-shared-secret
```

Without Pub/Sub, email sync happens at connection time and when users interact with contacts.

## OAuth Scopes

The Gmail integration requests these OAuth scopes:

| Scope | Purpose |
|-------|---------|
| `gmail.readonly` | Read email messages for syncing |
| `gmail.send` | Send emails on behalf of the user |
| `userinfo.email` | Identify the user's Gmail address |

## Per-User Connection

Gmail integration is per-user. Each CRM user connects their own Gmail account independently:

1. User navigates to **API Settings**.
2. Clicks **Connect Gmail**.
3. Authorizes access in the Google popup.
4. The CRM stores OAuth tokens (encrypted) for that user.

## Security Considerations

- OAuth tokens (access and refresh) are encrypted at rest using Fernet symmetric encryption (`TOKEN_ENCRYPTION_KEY`).
- A `TOKEN_ENCRYPTION_KEY` should be set in production (generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).
- Each user's Gmail access is independent -- one user cannot read another user's emails.
- Disconnecting revokes the OAuth token with Google.
- The CRM only accesses emails matching known contact email addresses during sync.
