# User Management

Only admin users can create and manage other user accounts.

## Roles

| Role | Permissions |
|------|-------------|
| **User** | Full CRUD on own resources. Read access to all shared data. |
| **Admin** | Everything a user can do, plus: create/edit/delete users, restore deleted opportunities, access audit logs. |

## Creating the First Admin User

In production, the database is not seeded with a demo account. Use the built-in CLI command to create your first admin user:

```bash
cd backend
python -m app.create_admin
```

You will be prompted for:

- **Email** -- Must be unique.
- **Full name** -- Display name for the account.
- **Password** -- Minimum 8 characters (entered twice for confirmation).

The command creates an active user with the **Admin** role. Once logged in, you can create additional users through the web UI.

> **Note:** If you are running with Docker, execute the command inside the backend container:
>
> ```bash
> docker compose exec backend python -m app.create_admin
> ```

## Creating a User

1. Log in as an admin.
2. Navigate to **Users** (visible in sidebar for admins only).
3. Click **Add User**.
4. Fill in:
   - **Name** -- User's display name.
   - **Email** -- Must be unique.
   - **Password** -- Minimum 8 characters.
   - **Role** -- User or Admin.
5. Click **Save**.

## Editing a User

1. Navigate to **Users**.
2. Click on the user to edit.
3. Modify fields as needed:
   - **Name**
   - **Email**
   - **Role** -- Promote or demote.
   - **Active** -- Enable or disable the account.
4. Click **Save**.

## Deactivating a User

Rather than deleting users (which would break data references), deactivate them:

1. Edit the user.
2. Set **Active** to disabled.
3. The user can no longer log in but their data remains intact.

## Google Sign-In Users

When a user signs in with Google for the first time and no matching email exists, a new user account is automatically created with the **User** role. To change their role to Admin, edit the user after their first sign-in.

Users who sign in with Google have their `auth_provider` set to `"google"`. They can also be assigned a local password if needed.

## API Keys

Each user can generate one API key for programmatic access. API keys are managed by users themselves via **API Settings**. Admins cannot view or generate API keys on behalf of users.

## Audit Trail

Sensitive operations (deleting accounts, contacts, opportunities, contracts) are recorded in the audit log, accessible to admin users at **Audit Log**.
