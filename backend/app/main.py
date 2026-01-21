from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, SessionLocal
from app.models.models import Base
from app.routers import auth, contacts, communications, contracts, contacts_followup, users, oidc_auth, queue
from app.seed_data import seed_database
import os

# Create database tables
Base.metadata.create_all(bind=engine)

# Seed database with initial data
db = SessionLocal()
try:
    seed_database(db)
finally:
    db.close()

app = FastAPI(
    title="Pretorin CRM API",
    description="API for managing sales contacts and government contract opportunities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Disable favicon
@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return {"detail": "Not Found"}

# Configure CORS
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8080")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:5173"],  # Vite default port as fallback
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(oidc_auth.router)
app.include_router(contacts.router)
app.include_router(contacts_followup.router)
app.include_router(communications.router)
app.include_router(contracts.router)
app.include_router(users.router)
app.include_router(queue.router)


@app.get("/")
def root():
    """API root endpoint"""
    return {
        "message": "Pretorin CRM API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
