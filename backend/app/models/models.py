from sqlalchemy import Boolean, Column, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

# Association table for many-to-many relationship between contracts and contacts
contract_contacts = Table(
    'contract_contacts',
    Base.metadata,
    Column('contract_id', String, ForeignKey('contracts.id')),
    Column('contact_id', String, ForeignKey('contacts.id'))
)

# Association table for tracking which users have acknowledged which contracts
contract_acknowledgments = Table(
    'contract_acknowledgments',
    Base.metadata,
    Column('contract_id', String, ForeignKey('contracts.id'), primary_key=True),
    Column('user_id', String, ForeignKey('users.id'), primary_key=True),
    Column('acknowledged_at', DateTime, default=datetime.utcnow)
)


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(String, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    phone = Column(String, nullable=False)
    organization = Column(String, nullable=False)
    contact_type = Column(String, nullable=False)  # individual, commercial, government
    status = Column(String, nullable=False)  # cold, warm, hot
    needs_follow_up = Column(Boolean, default=False)  # Deprecated - use follow_up_date instead
    follow_up_date = Column(DateTime, nullable=True)  # Target date to follow up
    notes = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_contacted_at = Column(DateTime, nullable=True)
    assigned_user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Queue fields
    created_via = Column(String, nullable=False, default="user")  # 'api' or 'user'
    is_claimed = Column(Boolean, nullable=False, default=True)    # False for API-created
    pending_acceptance = Column(Boolean, nullable=False, default=False)
    reassigned_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)

    # Relationships
    communications = relationship("Communication", back_populates="contact", cascade="all, delete-orphan")
    contracts = relationship("Contract", secondary=contract_contacts, back_populates="assigned_contacts")
    assigned_user = relationship("User", back_populates="assigned_contacts", foreign_keys=[assigned_user_id])
    reassigned_by_user = relationship("User", foreign_keys=[reassigned_by_user_id])


class Communication(Base):
    __tablename__ = "communications"

    id = Column(String, primary_key=True, index=True)
    contact_id = Column(String, ForeignKey("contacts.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    type = Column(String, nullable=False)  # email, phone, meeting, other
    notes = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    contact = relationship("Contact", back_populates="communications")


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, default="")
    source = Column(String, nullable=False)
    deadline = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)  # prospective, in progress, submitted, not a good fit
    submission_link = Column(String, nullable=True)
    notes = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Queue fields
    created_via = Column(String, nullable=False, default="user")
    is_claimed = Column(Boolean, nullable=False, default=True)
    claimed_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)

    # Relationships
    assigned_contacts = relationship("Contact", secondary=contract_contacts, back_populates="contracts")
    claimed_by_user = relationship("User", foreign_keys=[claimed_by_user_id])


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)  # Empty string for OIDC-only users
    role = Column(String, nullable=False, default="user")  # "admin" or "user"
    is_active = Column(Boolean, nullable=False, default=True)
    api_key = Column(String, unique=True, nullable=True, index=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    password_reset_token = Column(String, nullable=True, index=True)
    password_reset_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # OAuth fields
    auth_provider = Column(String, nullable=False, default="local")  # 'local' or 'google'
    google_id = Column(String, unique=True, nullable=True, index=True)  # Google OAuth subject ID

    # Relationships
    assigned_contacts = relationship("Contact", back_populates="assigned_user", foreign_keys="[Contact.assigned_user_id]")
    created_users = relationship("User", remote_side=[id])
