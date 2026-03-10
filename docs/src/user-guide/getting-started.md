# Getting Started

## Logging In

Navigate to the CRM login page (typically `http://localhost:5173` in development or your organization's URL in production).

### Email & Password

1. Enter your email address and password.
2. Click **Sign In**.
3. You'll be redirected to the Dashboard.

If you don't have an account, ask your administrator to create one for you.

### Google Sign-In

If your administrator has enabled Google authentication, a **Sign in with Google** button appears below the login form. (If you don't see it, the feature has not been configured -- see the [Google Authentication Setup](../admin-guide/google-auth-setup.md) admin guide.)

1. Click the **Sign in with Google** button.
2. Select your Google account in the popup.
3. You'll be automatically signed in and redirected to the Dashboard.

On first Google sign-in, an account is automatically created for you. If an account with your Google email already exists, it will be linked to your Google identity.

> **Note:** The Google Sign-In button is only visible when the `GOOGLE_CLIENT_ID` environment variable is configured.

### Forgot Password

1. Click **Forgot password?** on the login page.
2. Enter your email address.
3. Check your email for a reset link (valid for 24 hours).
4. Click the link and set a new password.

## Navigation

After logging in, the sidebar provides access to all major sections:

| Section | Description |
|---------|-------------|
| **Dashboard** | Overview of pipeline metrics, follow-ups, and key stats |
| **Pipeline** | Kanban board view of opportunities by stage |
| **Opportunities** | List view of all opportunities with filters |
| **Accounts** | Organizations (agencies, primes, subs, partners) |
| **Contacts** | People at accounts with follow-up tracking |
| **Vehicles** | Contract vehicles (GSA MAS, OASIS, etc.) |
| **Compliance** | Certification tracking with expiration alerts |
| **API Settings** | API key management and Gmail connection |

Admin users also see a **Users** section for managing user accounts.

## Changing Your Password

1. Navigate to **API Settings**.
2. Scroll to the **Change Password** section.
3. Enter your current password and your new password.
4. Click **Change Password**.

> **Note:** Google sign-in users who haven't set a local password can only authenticate via Google.
