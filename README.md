# Simple CRM

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-green.svg)
![Node](https://img.shields.io/badge/node-18+-green.svg)
![React](https://img.shields.io/badge/react-18-61dafb.svg)
![TypeScript](https://img.shields.io/badge/typescript-5-3178c6.svg)
![FastAPI](https://img.shields.io/badge/fastapi-latest-009688.svg)

A lightweight CRM designed for startups in the govtech space. This tool provides essential functionality for tracking government contract opportunities and managing business contacts.

## About

Simple CRM is a straightforward customer relationship management system built specifically for government technology companies. It offers an intuitive interface for managing contacts, tracking government contract opportunities, and logging communications. The application includes example data to help you understand the system quickly.

## Key Features

- **Contact Management**: Track individual, commercial, and government contacts with status indicators (hot/warm/cold)
- **Contract Opportunity Tracking**: Monitor government contract opportunities with deadlines and submission links
- **Follow-up System**: Flag contacts for follow-up with date tracking
- **Communication Logging**: Record all interactions with contacts (email, phone, meetings)
- **User Management**: Multi-user support with admin controls
- **API Integration**: RESTful API with JWT and API key authentication
- **Google Sign-In**: Optional Google identity provider login (see [Google Sign-In](#google-sign-in))
- **SAM.gov Integration**: Import contract opportunities from SAM.gov via the govbizops scraper
- **Gmail Integration**: Sync and send emails through the CRM per contact (see [Gmail Integration](#gmail-integration))
- **Observability**: Structured JSON logging, Prometheus metrics, Sentry error reporting, request ID correlation
- **Data Backups**: Scheduled PostgreSQL backups with retention management

## Technologies

**Frontend:**
- React with TypeScript
- Vite build tool
- shadcn/ui component library
- Tailwind CSS for styling
- React Router for navigation

**Backend:**
- Python FastAPI framework
- PostgreSQL database with SQLAlchemy ORM
- Alembic database migrations
- JWT token authentication with refresh tokens
- API key authentication for automation
- Pydantic for data validation
- Prometheus metrics and Sentry error reporting

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) (recommended)
- Or for local development: Node.js 18+, Python 3.12+, and a PostgreSQL instance

### Deploy with Docker Compose (Recommended)

The easiest way to run the full stack is with Docker Compose. This starts PostgreSQL, the backend API, and the frontend in one command:

```sh
git clone https://github.com/pretorin-ai/simple-crm.git
cd simple-crm
docker compose up --build
```

Once the containers are healthy:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **PostgreSQL**: `localhost:5432` (user: `crm`, password: `crm`, database: `crm`)

Press `Ctrl+C` to stop all services. Data is persisted in a Docker volume (`pgdata`).

#### Configuration

Environment variables can be overridden in a `.env` file at the project root or passed directly:

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `change-me-in-production` | JWT signing key |
| `TOKEN_ENCRYPTION_KEY` | *(empty)* | Fernet key for encrypting OAuth tokens at rest |
| `ENV` | `development` | Set to `production` to disable seed data and debug features |
| `LOG_LEVEL` | `info` | Logging level (`debug`, `info`, `warning`, `error`) |
| `VITE_API_BASE_URL` | `/api` (Docker) | Backend URL used by the frontend at build time |
| `GOOGLE_CLIENT_ID` | *(empty)* | Google OAuth2 client ID (used by both backend and frontend) |
| `GOOGLE_CLIENT_SECRET` | *(empty)* | Google OAuth2 client secret |
| `GOOGLE_REDIRECT_URI` | `{FRONTEND_URL}/api/gmail/callback` | OAuth2 callback URL (auto-derived if not set) |
| `GOOGLE_PUBSUB_TOPIC` | *(empty)* | Pub/Sub topic for Gmail push notifications |
| `GMAIL_WEBHOOK_TOKEN` | *(empty)* | Shared secret for verifying Gmail webhook requests |
| `SENTRY_DSN` | *(empty)* | Sentry DSN for error reporting (optional) |

Example production deployment:

```sh
SECRET_KEY=your-secure-secret ENV=production docker compose up --build -d
```

#### Useful Docker Compose Commands

```sh
docker compose up --build -d   # Start in background (rebuild images)
docker compose logs -f         # Follow all service logs
docker compose logs -f backend # Follow backend logs only
docker compose down            # Stop and remove containers
docker compose down -v         # Stop and remove containers + database volume
```

### Local Development Setup (Alternative)

If you prefer to run services directly for development:

**1. Start PostgreSQL** (or use an existing instance):
```sh
docker compose up db -d
```

**2. Set up and run the backend:**
```sh
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install .
cp .env.example .env      # Edit .env if your database connection differs
python run.py
```

**3. In a new terminal, set up and run the frontend:**
```sh
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

The frontend dev server runs at **http://localhost:5173** and the backend API at **http://localhost:8000**.

### Default Login

The example database includes a demo user:
- **Email**: demo@pretorin.com
- **Password**: demo1234

**Important**: Change this password in production environments.

## API Integration

Simple CRM provides a RESTful API with two authentication methods:

### JWT Token Authentication

Full access to all API endpoints using JWT bearer tokens. Tokens are obtained through the `/auth/login` endpoint.

### API Key Authentication

Limited access designed for automation and integrations. API keys can only access:
- `GET /contracts` - View all contracts (read-only)
- `POST /contracts/import/samgov` - Import contracts from SAM.gov
- `GET /auth/me` - Get authenticated user information

To generate an API key:
1. Log in to the application
2. Navigate to the API settings page
3. Click "Generate API Key"
4. Store the key securely (it will only be shown once)

### API Documentation

Once the backend is running, interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Development

### Frontend Commands

Run these from the `frontend/` directory:

- `npm run dev` - Start development server with hot reload
- `npm run build` - Build for production
- `npm run build:dev` - Build in development mode
- `npm run lint` - Run ESLint
- `npm run preview` - Preview production build locally
- `npm test` - Run tests (Vitest)
- `npm run test:watch` - Run tests in watch mode

### Backend Development

The backend runs with auto-reload enabled during development. Changes to Python files automatically restart the server.

To reset the database with fresh example data:
```sh
docker compose down -v         # Remove the database volume
docker compose up --build      # Recreate and re-seed
```

### Project Structure

```
simple-crm/
├── docker-compose.yml        # Full-stack deployment
├── backend/
│   ├── Dockerfile            # Backend container image
│   ├── entrypoint.sh         # Docker entrypoint (migrations + uvicorn)
│   ├── alembic/              # Database migrations
│   ├── app/
│   │   ├── auth.py           # Authentication logic
│   │   ├── encryption.py     # Fernet encryption for OAuth tokens
│   │   ├── logging_config.py # Structured JSON logging
│   │   ├── models/           # Database models
│   │   ├── routers/          # API route handlers
│   │   ├── services/         # Shared business logic
│   │   └── seed_data.py      # Example data seeder
│   ├── run.py                # Application entry point
│   └── pyproject.toml        # Python dependencies
├── frontend/
│   ├── Dockerfile            # Frontend container image (multi-stage)
│   ├── nginx.conf            # Production nginx config
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── contexts/         # React context providers
│   │   ├── lib/              # Utility functions and API client
│   │   └── pages/            # Page components
│   ├── package.json          # Frontend dependencies
│   └── vite.config.ts        # Vite configuration
└── scripts/
    ├── backup.sh             # Database backup with cron support
    ├── pre-commit            # Pre-commit checks (lint, test, build)
    ├── dev.sh                # Development launcher (Linux/Mac)
    └── dev.bat               # Development launcher (Windows)
```

## Google Sign-In

Users can sign in with their Google account instead of (or in addition to) email/password. The "Sign in with Google" button on the login page is **only visible when `GOOGLE_CLIENT_ID` is set**.

### Setup

1. Create a Google Cloud project and OAuth2 web credentials (see [Gmail Integration](#gmail-integration) step 1 if you haven't already)
2. In the OAuth2 credential, add your frontend URL as an **Authorized JavaScript origin** (e.g., `http://localhost:5173`)
3. Set `GOOGLE_CLIENT_ID` in your root `.env` (used by both backend and frontend):

   ```env
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   ```

4. Restart both services

The Sign-In button will now appear on the login page. On first Google sign-in, a user account is created automatically. If an account with the same email already exists, the Google identity is linked to it.

> **Note:** If `GOOGLE_CLIENT_ID` is not set, the login page shows only the email/password form.

## Gmail Integration

Connect your Gmail account to sync emails with contacts and send emails directly from the CRM.

### Capabilities

- **Automatic email sync** - Emails are synced automatically via Google Pub/Sub push notifications. New emails in the INBOX are matched to contacts by email address and appear in the contact's Communications tab with subject, sender, direction (sent/received), and full body.
- **Send emails** - Compose and send emails to contacts through Gmail without leaving the CRM. Sent emails are automatically logged as communications.
- **Reply threading** - Reply to received emails with proper Gmail threading preserved.
- **Per-user** - Each CRM user connects their own Gmail account independently.

### Setup

#### 1. Create Google Cloud Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the **Gmail API** and **Cloud Pub/Sub API**: navigate to **APIs & Services > Library**, search for each, and click **Enable**
4. Configure the **OAuth consent screen**:
   - Navigate to **APIs & Services > OAuth consent screen**
   - Choose **External** user type (or **Internal** if using Google Workspace)
   - Fill in app name, support email, and developer contact
   - Add scopes: `gmail.readonly`, `gmail.send`, `userinfo.email`
   - Add your email(s) as test users (required while the app is in "Testing" status)
5. Create **OAuth 2.0 credentials**:
   - Navigate to **APIs & Services > Credentials**
   - Click **Create Credentials > OAuth client ID**
   - Application type: **Web application**
   - Add authorized redirect URI: `http://localhost:8000/gmail/callback`
   - Copy the **Client ID** and **Client Secret**

#### 2. Configure Environment Variables

Add to your `backend/.env` (or your root `.env` for Docker Compose):

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/gmail/callback
GOOGLE_PUBSUB_TOPIC=projects/your-project/topics/gmail-push
```

To set up Pub/Sub for automatic sync:

1. Create a Pub/Sub topic (e.g., `gmail-push`) in Google Cloud Console
2. Create a push subscription pointing to `https://your-domain/gmail/webhook`
3. Grant `gmail-api-push@system.gserviceaccount.com` publish permission on the topic

#### 3. Connect Your Account

1. Log into the CRM
2. Go to **API & Integrations** (settings page)
3. Click **Connect Gmail** and authorize in the Google consent screen
4. You'll be redirected back with Gmail connected

#### 4. Usage

On any contact's detail page:

- Emails are synced automatically — new INBOX emails are pushed via Pub/Sub and matched to contacts
- **Email** button - compose a new email to the contact
- **Reply** link - reply to a received email (preserves Gmail threading)

### Production Notes

- Set `GOOGLE_REDIRECT_URI` to your production URL (e.g., `https://api.yourapp.com/gmail/callback`)
- Add the production redirect URI to Google Cloud Console authorized redirect URIs
- The Pub/Sub push subscription must point to your public `https://your-domain/gmail/webhook` endpoint
- Gmail watches expire after 7 days; the system auto-renews watches when they are within 1 day of expiry
- Submit your OAuth consent screen for Google verification if serving more than test users
- OAuth tokens are encrypted at rest with Fernet encryption when `TOKEN_ENCRYPTION_KEY` is set

## Security Notes

- API keys have limited access by design - they cannot modify or delete data beyond importing contracts
- JWT tokens provide full access and should be kept secure; refresh tokens extend sessions without re-authentication
- Gmail OAuth tokens are encrypted at rest via Fernet encryption (`TOKEN_ENCRYPTION_KEY`)
- Rate limiting protects authentication endpoints (login, register, token refresh, password reset)
- Change default passwords in production
- Use environment variables for sensitive configuration
- API keys should be rotated regularly
- Database CHECK constraints enforce valid enum values at the SQL level
- Structured JSON logging with request ID correlation enables tracing

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Related Projects

- [govbizops](https://github.com/pretorin-ai/govbizops) - SAM.gov scraper for automatically importing government contract opportunities
