# Gmail Integration

The Gmail integration connects your Gmail account to the CRM, enabling automatic email sync and in-app email sending.

## Prerequisites

- Your administrator must configure Google OAuth credentials. See the [Gmail Setup](../admin-guide/gmail-setup.md) section in the Administrator Guide.
- You need a Gmail or Google Workspace account.

## Connecting Gmail

1. Navigate to **API Settings**.
2. Under **Gmail Integration**, click **Connect Gmail**.
3. You'll be redirected to Google's consent screen.
4. Select your Google account and grant the requested permissions:
   - Read email messages
   - Send email
   - View email address
5. After granting access, you'll be redirected back to the CRM.
6. The status should show **Connected** with your Gmail address.

## How Email Sync Works

Once connected:

- **Initial Sync** -- The system performs a one-time sync of recent emails matching your CRM contacts.
- **Ongoing Sync** -- New emails are synced via Google Pub/Sub push notifications (if configured) or periodic checks.
- **Contact Matching** -- Emails are matched to contacts by comparing sender/recipient addresses with contact email addresses.

Synced emails appear as communications on the corresponding contact's detail page with full subject, body, and threading.

## Sending Email

From a contact's detail page:

1. Click **Send Email**.
2. Compose your email (subject and body).
3. To reply to an existing thread, click **Reply** on a synced email.
4. Click **Send**.

Sent emails are logged as outbound communications on the contact and appear in your Gmail Sent folder.

## Disconnecting Gmail

1. Navigate to **API Settings**.
2. Under **Gmail Integration**, click **Disconnect**.
3. This revokes the CRM's access to your Gmail account.

> **Note:** Disconnecting does not delete previously synced communications. Each user connects their own Gmail account independently.
