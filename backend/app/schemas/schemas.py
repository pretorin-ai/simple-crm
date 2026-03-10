from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Account schemas
AccountType = Literal["government_agency", "prime_contractor", "subcontractor", "partner", "vendor"]


class AccountBase(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    account_type: AccountType
    parent_agency: Optional[str] = Field(default=None, max_length=300)
    office: Optional[str] = Field(default=None, max_length=300)
    location: Optional[str] = Field(default=None, max_length=300)
    website: Optional[str] = Field(default=None, max_length=2048)
    notes: str = Field(default="", max_length=10000)


class AccountCreate(AccountBase):
    pass


class AccountUpdate(AccountBase):
    pass


class AccountPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=300)
    account_type: Optional[AccountType] = None
    parent_agency: Optional[str] = Field(default=None, max_length=300)
    office: Optional[str] = Field(default=None, max_length=300)
    location: Optional[str] = Field(default=None, max_length=300)
    website: Optional[str] = Field(default=None, max_length=2048)
    notes: Optional[str] = Field(default=None, max_length=10000)


class AccountBrief(BaseModel):
    id: str
    name: str
    account_type: str

    model_config = ConfigDict(from_attributes=True)


class Account(AccountBase):
    id: str
    created_by_user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Contact schemas
class ContactBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(max_length=50)
    organization: str = Field(max_length=200)
    contact_type: Literal["individual", "commercial", "government"]
    status: Literal["cold", "warm", "hot"]
    needs_follow_up: bool = False
    follow_up_date: Optional[datetime] = None
    notes: str = Field(default="", max_length=10000)


class ContactCreate(ContactBase):
    assigned_user_id: Optional[str] = None
    account_id: Optional[str] = None
    title: Optional[str] = Field(default=None, max_length=200)
    relationship_strength: Optional[str] = None


class ContactUpdate(ContactBase):
    last_contacted_at: Optional[datetime] = None
    assigned_user_id: str
    account_id: Optional[str] = None
    title: Optional[str] = Field(default=None, max_length=200)
    relationship_strength: Optional[str] = None


class ContactPatch(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=50)
    organization: Optional[str] = Field(default=None, max_length=200)
    contact_type: Optional[Literal["individual", "commercial", "government"]] = None
    status: Optional[Literal["cold", "warm", "hot"]] = None
    needs_follow_up: Optional[bool] = None
    follow_up_date: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=10000)
    last_contacted_at: Optional[datetime] = None
    assigned_user_id: Optional[str] = None
    account_id: Optional[str] = None
    title: Optional[str] = Field(default=None, max_length=200)
    relationship_strength: Optional[str] = None


class ContactBrief(BaseModel):
    id: str
    first_name: str
    last_name: str

    model_config = ConfigDict(from_attributes=True)


class Contact(ContactBase):
    id: str
    created_at: datetime
    last_contacted_at: Optional[datetime] = None
    assigned_user_id: str
    assigned_user: Optional["User"] = None
    account_id: Optional[str] = None
    title: Optional[str] = None
    relationship_strength: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Communication schemas
class CommunicationBase(BaseModel):
    contact_id: str
    date: datetime
    type: Literal["email", "phone", "meeting", "other"]
    notes: str = Field(default="", max_length=10000)


class CommunicationCreate(CommunicationBase):
    pass


class Communication(CommunicationBase):
    id: str
    created_at: datetime
    subject: Optional[str] = None
    email_from: Optional[str] = None
    email_to: Optional[str] = None
    body_html: Optional[str] = None
    gmail_message_id: Optional[str] = None
    gmail_thread_id: Optional[str] = None
    direction: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Gmail Integration schemas
class GmailIntegrationStatus(BaseModel):
    connected: bool
    gmail_address: Optional[str] = None
    last_sync_at: Optional[datetime] = None


class GmailAuthUrl(BaseModel):
    auth_url: str


class GmailSendRequest(BaseModel):
    to: EmailStr
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=50000)
    contact_id: str
    reply_to_message_id: Optional[str] = None
    thread_id: Optional[str] = None


class GoogleContactPreview(BaseModel):
    google_resource_name: str
    first_name: str
    last_name: str
    email: str
    phone: str = ""
    organization: str = ""
    title: str = ""
    already_exists: bool = False


class GoogleContactsPreviewResponse(BaseModel):
    contacts: List[GoogleContactPreview]
    total_fetched: int


class GoogleContactImportItem(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(max_length=100)
    email: EmailStr
    phone: str = Field(default="", max_length=50)
    organization: str = Field(default="", max_length=200)
    title: str = Field(default="", max_length=200)
    contact_type: Literal["individual", "commercial", "government"] = "individual"
    status: Literal["cold", "warm", "hot"] = "cold"


class GoogleContactImportRequest(BaseModel):
    contacts: List[GoogleContactImportItem] = Field(min_length=1, max_length=500)


class GoogleContactImportResponse(BaseModel):
    imported: int
    skipped: int
    errors: List[str] = []


# Contract schemas
class ContractBase(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=50000)
    source: str = Field(max_length=200)
    deadline: datetime
    status: Literal["prospective", "in progress", "submitted", "not a good fit"]
    submission_link: Optional[str] = Field(default=None, max_length=2048)
    notes: str = Field(default="", max_length=10000)


class ContractCreate(ContractBase):
    assigned_contact_ids: List[str] = []


class ContractUpdate(ContractBase):
    assigned_contact_ids: List[str] = []


class ContractPatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    description: Optional[str] = Field(default=None, max_length=50000)
    source: Optional[str] = Field(default=None, max_length=200)
    deadline: Optional[datetime] = None
    status: Optional[Literal["prospective", "in progress", "submitted", "not a good fit"]] = None
    submission_link: Optional[str] = Field(default=None, max_length=2048)
    notes: Optional[str] = Field(default=None, max_length=10000)
    assigned_contact_ids: Optional[List[str]] = None


class Contract(ContractBase):
    id: str
    created_at: datetime
    created_by_user_id: Optional[str] = None
    assigned_contact_ids: List[str] = []
    assigned_contacts: List[ContactBrief] = []

    model_config = ConfigDict(from_attributes=True)


# SAM.gov Import schemas
class SAMGovPointOfContact(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    fullName: Optional[str] = None
    type: Optional[str] = None


class SAMGovOpportunity(BaseModel):
    noticeId: str = Field(max_length=255)
    title: str = Field(max_length=300)
    solicitationNumber: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=50000)
    responseDeadLine: Optional[str] = None
    postedDate: Optional[str] = None
    naicsCode: Optional[str] = Field(default=None, max_length=20)
    uiLink: Optional[str] = Field(default=None, max_length=2048)
    pointOfContact: Optional[List[SAMGovPointOfContact]] = None
    source: str = "SAM.gov"
    notes: Optional[str] = Field(default="", max_length=10000)


class SAMGovImportRequest(BaseModel):
    opportunities: List[SAMGovOpportunity]
    auto_create_contacts: bool = True


class SAMGovImportResponse(BaseModel):
    contracts_created: int
    contracts_skipped: int
    contacts_created: int
    errors: List[str] = []


# SAM.gov collection schemas (direct API scraping)
class SAMGovCollectRequest(BaseModel):
    naics_codes: List[str] = Field(min_length=1, max_length=50)
    days_back: int = Field(default=1, ge=1, le=90)
    solicitations_only: bool = True
    auto_create_contacts: bool = True


class SAMGovCollectResponse(BaseModel):
    opportunities_fetched: int
    contracts_created: int
    contracts_skipped: int
    contacts_created: int
    errors: List[str] = []


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=150)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserCreateByAdmin(UserBase):
    password: str = Field(min_length=8, max_length=128)
    role: Literal["admin", "user"] = "user"


class UserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    email: Optional[EmailStr] = None
    role: Optional[Literal["admin", "user"]] = None
    is_active: Optional[bool] = None


class User(UserBase):
    id: str
    role: str
    is_active: bool
    auth_provider: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Password reset schemas
class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


# Auth schemas
class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    email: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    credential: str = Field(min_length=1)


# Opportunity schemas
OpportunityStage = Literal[
    "identified", "qualified", "capture", "teaming", "proposal", "submitted", "awarded", "lost"
]
SetAsideType = Literal["small_business", "8a", "hubzone", "wosb", "sdvosb", "full_and_open", "none"]
OpportunitySource = Literal[
    "sam_gov", "agency_forecast", "incumbent_recompete", "partner_referral", "internal"
]


class OpportunityBase(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    is_government_contract: bool = False
    description: str = Field(default="", max_length=50000)
    agency: Optional[str] = Field(default=None, max_length=300)
    account_id: Optional[str] = None
    naics_code: Optional[str] = Field(default=None, max_length=20)
    set_aside_type: Optional[SetAsideType] = None
    estimated_value: Optional[float] = None
    solicitation_number: Optional[str] = Field(default=None, max_length=255)
    sam_gov_notice_id: Optional[str] = Field(default=None, max_length=255)
    submission_link: Optional[str] = Field(default=None, max_length=2048)
    deadline: Optional[datetime] = None
    source: Optional[OpportunitySource] = None
    stage: OpportunityStage = "identified"
    capture_manager_id: Optional[str] = None
    expected_release_date: Optional[datetime] = None
    proposal_due_date: Optional[datetime] = None
    award_date_estimate: Optional[datetime] = None
    win_probability: Optional[int] = Field(default=None, ge=0, le=100)
    notes: str = Field(default="", max_length=10000)


class OpportunityCreate(OpportunityBase):
    vehicle_ids: List[str] = []


class OpportunityUpdate(OpportunityBase):
    vehicle_ids: List[str] = []


class OpportunityPatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    is_government_contract: Optional[bool] = None
    description: Optional[str] = Field(default=None, max_length=50000)
    agency: Optional[str] = Field(default=None, max_length=300)
    account_id: Optional[str] = None
    naics_code: Optional[str] = Field(default=None, max_length=20)
    set_aside_type: Optional[SetAsideType] = None
    estimated_value: Optional[float] = None
    solicitation_number: Optional[str] = Field(default=None, max_length=255)
    sam_gov_notice_id: Optional[str] = Field(default=None, max_length=255)
    submission_link: Optional[str] = Field(default=None, max_length=2048)
    deadline: Optional[datetime] = None
    source: Optional[OpportunitySource] = None
    stage: Optional[OpportunityStage] = None
    capture_manager_id: Optional[str] = None
    expected_release_date: Optional[datetime] = None
    proposal_due_date: Optional[datetime] = None
    award_date_estimate: Optional[datetime] = None
    win_probability: Optional[int] = Field(default=None, ge=0, le=100)
    notes: Optional[str] = Field(default=None, max_length=10000)
    vehicle_ids: Optional[List[str]] = None


class VehicleBrief(BaseModel):
    id: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class Opportunity(OpportunityBase):
    id: str
    created_at: datetime
    updated_at: datetime
    created_by_user_id: Optional[str] = None
    deleted_at: Optional[datetime] = None
    vehicle_ids: List[str] = []
    vehicles: List[VehicleBrief] = []

    model_config = ConfigDict(from_attributes=True)


# Contract Vehicle schemas
class ContractVehicleBase(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    agency: Optional[str] = Field(default=None, max_length=300)
    contract_number: Optional[str] = Field(default=None, max_length=255)
    expiration_date: Optional[datetime] = None
    ceiling_value: Optional[float] = None
    prime_or_sub: Optional[Literal["prime", "sub"]] = None
    notes: str = Field(default="", max_length=10000)


class ContractVehicleCreate(ContractVehicleBase):
    pass


class ContractVehicleUpdate(ContractVehicleBase):
    pass


class ContractVehiclePatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=300)
    agency: Optional[str] = Field(default=None, max_length=300)
    contract_number: Optional[str] = Field(default=None, max_length=255)
    expiration_date: Optional[datetime] = None
    ceiling_value: Optional[float] = None
    prime_or_sub: Optional[Literal["prime", "sub"]] = None
    notes: Optional[str] = Field(default=None, max_length=10000)


class ContractVehicle(ContractVehicleBase):
    id: str
    created_by_user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Teaming schemas
TeamingRole = Literal["prime", "subcontractor", "jv_partner"]
TeamingStatus = Literal["potential", "nda_signed", "teaming_agreed", "active", "inactive"]


class TeamingBase(BaseModel):
    opportunity_id: str
    partner_account_id: str
    role: TeamingRole
    status: TeamingStatus = "potential"
    notes: str = Field(default="", max_length=10000)


class TeamingCreate(TeamingBase):
    pass


class TeamingUpdate(TeamingBase):
    pass


class TeamingPatch(BaseModel):
    role: Optional[TeamingRole] = None
    status: Optional[TeamingStatus] = None
    notes: Optional[str] = Field(default=None, max_length=10000)


class Teaming(TeamingBase):
    id: str
    created_at: datetime
    updated_at: datetime
    partner_account: Optional[AccountBrief] = None

    model_config = ConfigDict(from_attributes=True)


# Proposal schemas
ProposalStatus = Literal["not_started", "in_progress", "review", "final", "submitted"]
SubmissionType = Literal["full", "partial", "draft"]


class ProposalBase(BaseModel):
    opportunity_id: str
    proposal_manager_id: Optional[str] = None
    submission_type: Optional[SubmissionType] = None
    submission_deadline: Optional[datetime] = None
    status: ProposalStatus = "not_started"
    notes: str = Field(default="", max_length=10000)


class ProposalCreate(ProposalBase):
    pass


class ProposalUpdate(ProposalBase):
    pass


class ProposalPatch(BaseModel):
    proposal_manager_id: Optional[str] = None
    submission_type: Optional[SubmissionType] = None
    submission_deadline: Optional[datetime] = None
    status: Optional[ProposalStatus] = None
    notes: Optional[str] = Field(default=None, max_length=10000)


class Proposal(ProposalBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Compliance schemas
CertificationType = Literal["small_business", "8a", "hubzone", "wosb", "sdvosb", "edwosb"]
ComplianceStatus = Literal["active", "expiring_soon", "expired", "pending"]


class ComplianceBase(BaseModel):
    certification_type: CertificationType
    issued_by: Optional[str] = Field(default=None, max_length=300)
    issue_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    status: ComplianceStatus = "active"
    notes: str = Field(default="", max_length=10000)


class ComplianceCreate(ComplianceBase):
    pass


class ComplianceUpdate(ComplianceBase):
    pass


class CompliancePatch(BaseModel):
    certification_type: Optional[CertificationType] = None
    issued_by: Optional[str] = Field(default=None, max_length=300)
    issue_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    status: Optional[ComplianceStatus] = None
    notes: Optional[str] = Field(default=None, max_length=10000)


class Compliance(ComplianceBase):
    id: str
    created_by_user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Opportunity Timeline schemas
OpportunityEventType = Literal[
    "discovery",
    "contact",
    "rfp_release",
    "proposal_submitted",
    "meeting",
    "stage_change",
    "note",
    "other",
]


class OpportunityEventCreate(BaseModel):
    opportunity_id: str
    date: datetime
    event_type: OpportunityEventType
    description: str = Field(min_length=1, max_length=10000)


class OpportunityEventUpdate(BaseModel):
    date: Optional[datetime] = None
    event_type: Optional[OpportunityEventType] = None
    description: Optional[str] = Field(default=None, min_length=1, max_length=10000)


class OpportunityEvent(BaseModel):
    id: str
    opportunity_id: str
    date: datetime
    event_type: str
    description: str
    created_by_user_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Capture Notes schemas
CaptureNoteSection = Literal[
    "customer_intel", "incumbent", "competitors", "partners", "risks", "strategy"
]


class CaptureNoteCreate(BaseModel):
    opportunity_id: str
    section: CaptureNoteSection
    content: str = Field(default="", max_length=50000)


class CaptureNoteUpdate(BaseModel):
    content: str = Field(max_length=50000)


class CaptureNote(BaseModel):
    id: str
    opportunity_id: str
    section: str
    content: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Attachment schemas
class AttachmentSchema(BaseModel):
    id: str
    opportunity_id: str
    filename: str
    content_type: Optional[str] = None
    size: Optional[int] = None
    uploaded_by_user_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Audit Log schemas
class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    action: str
    entity_type: str
    entity_id: str
    details: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Pipeline/Reporting schemas
class PipelineMetrics(BaseModel):
    total_opportunities: int
    pipeline_value: float
    expected_award_revenue: float
    win_rate: float
    average_deal_size: float
    by_stage: dict
    by_agency: dict
