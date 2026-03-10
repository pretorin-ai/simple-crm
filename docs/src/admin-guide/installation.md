# Installation

Pretorin CRM can be run in development mode directly on your machine or deployed with Docker.

## Prerequisites

- **Python 3.12+**
- **Node.js 18+** and npm
- **PostgreSQL 16** (production) or SQLite (development)
- **Git**

## Quick Start (Development)

### 1. Clone the repository

```bash
git clone https://github.com/pretorin/simple-crm.git
cd simple-crm
```

### 2. Backend setup

```bash
cd backend

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env and set at minimum:
#   SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_hex(32))")
#   DATABASE_URL (default sqlite:///./crm.db works for development)
```

### 3. Frontend setup

```bash
cd ../frontend

# Install dependencies
npm install
```

### 4. Run both services

Using the included development script:

```bash
cd ..
./scripts/dev.sh    # Linux/Mac
# scripts\dev.bat   # Windows
```

Or manually:

```bash
# Terminal 1 - Backend
cd backend
source .venv/bin/activate
python run.py
# Runs on http://localhost:8000

# Terminal 2 - Frontend
cd frontend
npm run dev
# Runs on http://localhost:5173
```

### 5. Access the CRM

Open `http://localhost:5173` in your browser. Default credentials:

- **Email:** `demo@pretorin.com`
- **Password:** `demo1234`

> **Important:** Change the default credentials immediately in any non-development environment.

## Database Options

### SQLite (Development)

No additional setup needed. Set in `.env`:

```
DATABASE_URL=sqlite:///./crm.db
```

### PostgreSQL (Production)

Install PostgreSQL and create a database:

```bash
createdb crm
```

Set in `.env`:

```
DATABASE_URL=postgresql://user:password@localhost:5432/crm
```

Tables are created via Alembic migrations. In Docker, migrations run automatically on container start. For local development:

```bash
cd backend
alembic upgrade head
```
