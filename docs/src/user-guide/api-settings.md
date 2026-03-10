# API Keys & Settings

The API Settings page provides access to API key management, Gmail integration, and password changes.

## API Keys

API keys allow external tools and scripts to authenticate with the CRM's REST API.

### Generating an API Key

1. Navigate to **API Settings**.
2. Under **API Key**, click **Generate API Key**.
3. Copy the key immediately -- it will only be shown once.
4. The key prefix (e.g., `crm_a1b2c3d4e5f6...`) is displayed for reference.

### Using an API Key

Include the API key in the `Authorization` header:

```
Authorization: Bearer crm_your_api_key_here
```

API keys work with all endpoints that accept JWT authentication (via the `/auth/me` endpoint and any protected route).

### Revoking an API Key

1. Navigate to **API Settings**.
2. Click **Revoke API Key**.
3. The old key is immediately invalidated.

You can generate a new key at any time. Only one key is active per user.

## Password Management

Under **Change Password**:

1. Enter your current password.
2. Enter your new password (minimum 8 characters).
3. Click **Change Password**.

## Gmail Integration

See [Gmail Integration](./gmail-integration.md) for details on connecting and using Gmail.
