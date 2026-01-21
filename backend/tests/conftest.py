"""
Test configuration and fixtures for the CRM backend.
"""
import os
import pytest
from datetime import datetime, timedelta, UTC
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

from app.main import app
from app.database import Base, get_db
from app.models.models import User, Contact, Contract, Communication
from app.auth import create_access_token, generate_api_key
from app.seed_data import generate_id


# Create test database engine with in-memory SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the database dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client with fresh database."""
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def admin_user(db) -> User:
    """Create an admin user for testing."""
    user = User(
        id=generate_id(),
        email="admin@test.com",
        name="Test Admin",
        hashed_password=None,
        auth_provider="google",
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def regular_user(db) -> User:
    """Create a regular user for testing."""
    user = User(
        id=generate_id(),
        email="user@test.com",
        name="Test User",
        hashed_password=None,
        auth_provider="google",
        role="user",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def inactive_user(db) -> User:
    """Create an inactive user for testing."""
    user = User(
        id=generate_id(),
        email="inactive@test.com",
        name="Inactive User",
        hashed_password=None,
        auth_provider="google",
        role="user",
        is_active=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_with_api_key(db) -> User:
    """Create a user with an API key for testing."""
    api_key = generate_api_key()
    user = User(
        id=generate_id(),
        email="apiuser@test.com",
        name="API User",
        hashed_password=None,
        auth_provider="google",
        role="user",
        is_active=True,
        api_key=api_key,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user) -> str:
    """Create a JWT token for the admin user."""
    return create_access_token(
        data={"sub": admin_user.email},
        expires_delta=timedelta(minutes=30)
    )


@pytest.fixture
def user_token(regular_user) -> str:
    """Create a JWT token for the regular user."""
    return create_access_token(
        data={"sub": regular_user.email},
        expires_delta=timedelta(minutes=30)
    )


@pytest.fixture
def inactive_user_token(inactive_user) -> str:
    """Create a JWT token for the inactive user."""
    return create_access_token(
        data={"sub": inactive_user.email},
        expires_delta=timedelta(minutes=30)
    )


@pytest.fixture
def admin_headers(admin_token) -> dict:
    """Authorization headers for admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def user_headers(user_token) -> dict:
    """Authorization headers for regular user."""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def api_key_headers(user_with_api_key) -> dict:
    """Authorization headers using API key."""
    return {"Authorization": f"Bearer {user_with_api_key.api_key}"}


@pytest.fixture
def sample_contact(db, regular_user) -> Contact:
    """Create a sample contact for testing."""
    contact = Contact(
        id=generate_id(),
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="555-1234",
        organization="Test Corp",
        contact_type="commercial",
        status="warm",
        notes="Test contact",
        assigned_user_id=regular_user.id,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@pytest.fixture
def sample_contract(db) -> Contract:
    """Create a sample contract for testing."""
    contract = Contract(
        id=generate_id(),
        title="Test Contract",
        description="A test contract",
        source="SAM.gov",
        deadline=datetime.now(UTC) + timedelta(days=30),
        status="prospective",
        notes="Test notes",
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract
