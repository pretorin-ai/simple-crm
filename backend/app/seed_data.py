from datetime import datetime, timedelta, UTC
from app.models.models import Contact, Communication, Contract, User
from app.auth import get_password_hash
import uuid


def generate_id():
    """Generate a unique ID"""
    return str(uuid.uuid4())


def get_seed_contacts(user_id):
    """Return seed data for contacts"""
    base_date = datetime.now(UTC)

    return [
        Contact(
            id=generate_id(),
            first_name="Sarah",
            last_name="Johnson",
            email="sarah.johnson@defense.gov",
            phone="(555) 123-4567",
            organization="Department of Defense",
            contact_type="government",
            status="hot",
            needs_follow_up=True,
            follow_up_date=base_date + timedelta(days=2),  # Due in 2 days
            notes="Key decision maker for cybersecurity initiatives. Very interested in our compliance automation platform.",
            created_at=base_date - timedelta(days=30),
            last_contacted_at=base_date - timedelta(days=3),
            assigned_user_id=user_id
        ),
        Contact(
            id=generate_id(),
            first_name="Michael",
            last_name="Chen",
            email="m.chen@techcorp.com",
            phone="(555) 234-5678",
            organization="TechCorp Solutions",
            contact_type="individual",
            status="warm",
            needs_follow_up=False,
            follow_up_date=base_date + timedelta(days=14),  # Due in 2 weeks
            notes="Software architect interested in our API. Follow up in 2 weeks.",
            created_at=base_date - timedelta(days=45),
            last_contacted_at=base_date - timedelta(days=14),
            assigned_user_id=user_id
        ),
        Contact(
            id=generate_id(),
            first_name="Emily",
            last_name="Rodriguez",
            email="emily.r@gsa.gov",
            phone="(555) 345-6789",
            organization="General Services Administration",
            contact_type="government",
            status="warm",
            needs_follow_up=True,
            follow_up_date=base_date - timedelta(days=1),  # Overdue by 1 day
            notes="Procurement officer. Mentioned upcoming RFP for compliance tools.",
            created_at=base_date - timedelta(days=60),
            last_contacted_at=base_date - timedelta(days=7),
            assigned_user_id=user_id
        ),
        Contact(
            id=generate_id(),
            first_name="David",
            last_name="Thompson",
            email="david.thompson@consultant.com",
            phone="(555) 456-7890",
            organization="Thompson Consulting",
            contact_type="commercial",
            status="cold",
            needs_follow_up=False,
            notes="Independent consultant. Potential partner for government contracts.",
            created_at=base_date - timedelta(days=90),
            last_contacted_at=None,
            assigned_user_id=user_id
        ),
        Contact(
            id=generate_id(),
            first_name="Jennifer",
            last_name="Martinez",
            email="j.martinez@dhs.gov",
            phone="(555) 567-8901",
            organization="Department of Homeland Security",
            contact_type="government",
            status="hot",
            needs_follow_up=True,
            follow_up_date=base_date,  # Due today
            notes="CISO - very interested in FedRAMP automation. Schedule demo next week.",
            created_at=base_date - timedelta(days=15),
            last_contacted_at=base_date - timedelta(days=1),
            assigned_user_id=user_id
        ),
    ]


def get_seed_communications(contacts):
    """Return seed data for communications"""
    base_date = datetime.now(UTC)

    # Assuming first contact is Sarah Johnson
    sarah_id = contacts[0].id if contacts else generate_id()
    emily_id = contacts[2].id if len(contacts) > 2 else generate_id()
    jennifer_id = contacts[4].id if len(contacts) > 4 else generate_id()

    return [
        Communication(
            id=generate_id(),
            contact_id=sarah_id,
            date=base_date - timedelta(days=3),
            type="email",
            notes="Sent product demo video and pricing information. Very positive response.",
            created_at=base_date - timedelta(days=3)
        ),
        Communication(
            id=generate_id(),
            contact_id=sarah_id,
            date=base_date - timedelta(days=10),
            type="meeting",
            notes="Initial discovery call. 45 minutes. Discussed current pain points with compliance processes.",
            created_at=base_date - timedelta(days=10)
        ),
        Communication(
            id=generate_id(),
            contact_id=emily_id,
            date=base_date - timedelta(days=7),
            type="phone",
            notes="15-minute call to clarify RFP requirements. Confirmed we meet all prerequisites.",
            created_at=base_date - timedelta(days=7)
        ),
        Communication(
            id=generate_id(),
            contact_id=jennifer_id,
            date=base_date - timedelta(days=1),
            type="email",
            notes="Shared FedRAMP automation case study. Requested demo for her team.",
            created_at=base_date - timedelta(days=1)
        ),
    ]


def get_seed_contracts(contacts):
    """Return seed data for contracts"""
    base_date = datetime.now(UTC)

    sarah_id = contacts[0].id if contacts else generate_id()
    emily_id = contacts[2].id if len(contacts) > 2 else generate_id()
    jennifer_id = contacts[4].id if len(contacts) > 4 else generate_id()

    contracts = [
        Contract(
            id=generate_id(),
            title="DoD Cybersecurity Compliance Automation",
            description="RFP for automated compliance monitoring and reporting system for DoD networks.",
            source="SAM.gov",
            deadline=base_date + timedelta(days=30),
            status="in progress",
            submission_link="https://sam.gov/opp/12345",
            notes="High priority. Working with Sarah Johnson. Need to submit technical approach by next Friday.",
            created_at=base_date - timedelta(days=20),
        ),
        Contract(
            id=generate_id(),
            title="GSA FedRAMP Package Acceleration",
            description="Tool to streamline FedRAMP authorization package preparation and submission.",
            source="GSA eBuy",
            deadline=base_date + timedelta(days=45),
            status="prospective",
            submission_link="https://ebuy.gsa.gov/12345",
            notes="Good fit for our platform. Need to qualify as small business first.",
            created_at=base_date - timedelta(days=10),
        ),
        Contract(
            id=generate_id(),
            title="DHS Security Assessment Automation",
            description="Automated security assessment tools for critical infrastructure.",
            source="DHS Procurement",
            deadline=base_date + timedelta(days=60),
            status="in progress",
            submission_link=None,
            notes="Jennifer Martinez is the primary contact. Demo scheduled for next week.",
            created_at=base_date - timedelta(days=5),
        ),
        Contract(
            id=generate_id(),
            title="Legacy System Migration Support",
            description="Support services for migrating legacy compliance systems to modern platforms.",
            source="Private Sector RFP",
            deadline=base_date - timedelta(days=15),
            status="not a good fit",
            submission_link=None,
            notes="Too focused on manual consulting. Not aligned with our automation approach.",
            created_at=base_date - timedelta(days=90),
        ),
    ]

    # Assign contacts to contracts
    contracts[0].assigned_contacts = [contacts[0]] if contacts else []
    contracts[1].assigned_contacts = [contacts[2]] if len(contacts) > 2 else []
    contracts[2].assigned_contacts = [contacts[4]] if len(contacts) > 4 else []

    return contracts


def seed_database(db):
    """
    Seed the database with initial data.

    In SSO-only mode, no seed data is created. The first user to sign in
    via Google OAuth will automatically become an admin.
    """
    # SSO-only mode: no seed data needed
    # The first user to authenticate via Google becomes admin automatically
    print("SSO-only mode: No seed data created.")
    print("The first user to sign in via Google will become admin.")
