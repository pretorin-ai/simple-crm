from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# Contact schemas
class ContactBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    organization: str
    contact_type: str
    status: str
    needs_follow_up: bool = False
    follow_up_date: Optional[datetime] = None
    notes: str = ""


class ContactCreate(ContactBase):
    assigned_user_id: Optional[str] = None  # Optional - will default to current user if not provided


class ContactUpdate(ContactBase):
    last_contacted_at: Optional[datetime] = None
    assigned_user_id: str


class Contact(ContactBase):
    id: str
    created_at: datetime
    last_contacted_at: Optional[datetime] = None
    assigned_user_id: str
    assigned_user: Optional["User"] = None

    class Config:
        from_attributes = True


# Communication schemas
class CommunicationBase(BaseModel):
    contact_id: str
    date: datetime
    type: str
    notes: str = ""


class CommunicationCreate(CommunicationBase):
    pass


class Communication(CommunicationBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


# Contract schemas
class ContractBase(BaseModel):
    title: str
    description: str = ""
    source: str
    deadline: datetime
    status: str
    submission_link: Optional[str] = None
    notes: str = ""


class ContractCreate(ContractBase):
    assigned_contact_ids: List[str] = []


class ContractUpdate(ContractBase):
    assigned_contact_ids: List[str] = []


class Contract(ContractBase):
    id: str
    created_at: datetime
    assigned_contact_ids: List[str] = []

    class Config:
        from_attributes = True


# SAM.gov Import schemas
class SAMGovPointOfContact(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    fullName: Optional[str] = None
    type: Optional[str] = None


class SAMGovOpportunity(BaseModel):
    noticeId: str
    title: str
    solicitationNumber: Optional[str] = None
    description: Optional[str] = None
    responseDeadLine: Optional[str] = None
    postedDate: Optional[str] = None
    naicsCode: Optional[str] = None
    uiLink: Optional[str] = None
    pointOfContact: Optional[List[SAMGovPointOfContact]] = None
    source: str = "SAM.gov"
    notes: Optional[str] = ""


class SAMGovImportRequest(BaseModel):
    opportunities: List[SAMGovOpportunity]
    auto_create_contacts: bool = True


class SAMGovImportResponse(BaseModel):
    contracts_created: int
    contracts_skipped: int
    contacts_created: int
    errors: List[str] = []


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreateByAdmin(UserBase):
    password: str
    role: str = "user"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class User(UserBase):
    id: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Password reset schemas
class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
