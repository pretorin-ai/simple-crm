# Contacts

Contacts are people at accounts that you communicate with. Each contact is assigned to a CRM user and can be linked to an account.

## Contact Fields

| Field | Description |
|-------|-------------|
| **Name** | First and last name |
| **Email** | Email address (used for Gmail matching) |
| **Phone** | Phone number |
| **Organization** | Company or agency name |
| **Title** | Job title |
| **Contact Type** | Individual, Commercial, or Government |
| **Status** | Cold, Warm, or Hot (relationship temperature) |
| **Account** | Linked account (optional) |
| **Relationship Strength** | Role-based label (e.g., Contracting Officer) |
| **Assigned User** | CRM user responsible for this contact |

## Creating a Contact

1. Navigate to **Contacts**.
2. Click **Add Contact**.
3. Fill in the required fields (name, email, phone, organization, type, status).
4. Optionally link to an account and assign to a user.
5. Click **Save**.

## Follow-Up Tracking

Contacts support follow-up reminders:

1. On the contact detail page, toggle **Needs Follow-Up**.
2. Set a **Follow-Up Date**.
3. Contacts with upcoming or overdue follow-ups appear on the Dashboard.

Follow-ups can be viewed in bulk:
- **Due Follow-Ups** -- Contacts with follow-ups due within a configurable window.
- **Overdue Follow-Ups** -- Contacts past their follow-up date.

## Communications

The contact detail page shows all communications (emails, phone calls, meetings) logged for that contact.

### Logging a Communication

1. On the contact detail page, click **Log Communication**.
2. Select the type (Email, Phone, Meeting, Other).
3. Set the date and add notes.
4. Click **Save**.

### Gmail Integration

If Gmail is connected, emails to/from the contact's email address are automatically synced and displayed. You can also send emails directly from the contact page. See [Gmail Integration](./gmail-integration.md) for setup.

## Deleting a Contact

Deleting a contact also removes all associated communications. This action is audited.
