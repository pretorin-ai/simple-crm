import logging
import os
from datetime import datetime, timedelta, timezone

from app.auth import get_password_hash
from app.models.models import (
    Account,
    Communication,
    Compliance,
    Contact,
    Contract,
    ContractVehicle,
    Opportunity,
    Proposal,
    Teaming,
    User,
)
from app.utils import generate_id

logger = logging.getLogger(__name__)


def get_seed_contacts(user_id):
    """Return seed data for contacts"""
    base_date = datetime.now(timezone.utc)

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
            notes=(
                "Key decision maker for cybersecurity initiatives."
                " Very interested in our compliance automation platform."
            ),
            created_at=base_date - timedelta(days=30),
            last_contacted_at=base_date - timedelta(days=3),
            assigned_user_id=user_id,
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
            assigned_user_id=user_id,
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
            assigned_user_id=user_id,
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
            assigned_user_id=user_id,
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
            assigned_user_id=user_id,
        ),
    ]


def get_seed_communications(contacts):
    """Return seed data for communications"""
    base_date = datetime.now(timezone.utc)

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
            created_at=base_date - timedelta(days=3),
        ),
        Communication(
            id=generate_id(),
            contact_id=sarah_id,
            date=base_date - timedelta(days=10),
            type="meeting",
            notes=(
                "Initial discovery call. 45 minutes."
                " Discussed current pain points with compliance processes."
            ),
            created_at=base_date - timedelta(days=10),
        ),
        Communication(
            id=generate_id(),
            contact_id=emily_id,
            date=base_date - timedelta(days=7),
            type="phone",
            notes=(
                "15-minute call to clarify RFP requirements. Confirmed we meet all prerequisites."
            ),
            created_at=base_date - timedelta(days=7),
        ),
        Communication(
            id=generate_id(),
            contact_id=jennifer_id,
            date=base_date - timedelta(days=1),
            type="email",
            notes="Shared FedRAMP automation case study. Requested demo for her team.",
            created_at=base_date - timedelta(days=1),
        ),
    ]


def get_seed_contracts(contacts):
    """Return seed data for contracts"""
    base_date = datetime.now(timezone.utc)

    contracts = [
        Contract(
            id=generate_id(),
            title="DoD Cybersecurity Compliance Automation",
            description=(
                "RFP for automated compliance monitoring and reporting system for DoD networks."
            ),
            source="SAM.gov",
            deadline=base_date + timedelta(days=30),
            status="in progress",
            submission_link="https://sam.gov/opp/12345",
            notes=(
                "High priority. Working with Sarah Johnson."
                " Need to submit technical approach by next Friday."
            ),
            created_at=base_date - timedelta(days=20),
        ),
        Contract(
            id=generate_id(),
            title="GSA FedRAMP Package Acceleration",
            description=(
                "Tool to streamline FedRAMP authorization package preparation and submission."
            ),
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
            description=(
                "Support services for migrating legacy compliance systems to modern platforms."
            ),
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


def get_seed_user():
    """Return seed user (default credentials: demo@pretorin.com / demo1234)"""
    return User(
        id=generate_id(),
        email="demo@pretorin.com",
        name="Demo Admin User",
        hashed_password=get_password_hash("demo1234"),
        role="admin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


def get_seed_accounts():
    """Return seed data for accounts (organizations)"""
    return [
        Account(
            id=generate_id(),
            name="Department of Defense",
            account_type="government_agency",
            parent_agency=None,
            office="Office of the CIO",
            location="Washington, DC",
            website="https://www.defense.gov",
            notes="Primary DoD engagement for cybersecurity contracts.",
        ),
        Account(
            id=generate_id(),
            name="General Services Administration",
            account_type="government_agency",
            parent_agency=None,
            office="Federal Acquisition Service",
            location="Washington, DC",
            website="https://www.gsa.gov",
            notes="GSA Schedule holder. Key procurement partner.",
        ),
        Account(
            id=generate_id(),
            name="Department of Homeland Security",
            account_type="government_agency",
            parent_agency=None,
            office="Cybersecurity and Infrastructure Security Agency",
            location="Arlington, VA",
            website="https://www.dhs.gov",
            notes="CISA engagement for critical infrastructure protection.",
        ),
        Account(
            id=generate_id(),
            name="Booz Allen Hamilton",
            account_type="prime_contractor",
            parent_agency=None,
            office=None,
            location="McLean, VA",
            website="https://www.boozallen.com",
            notes="Major prime contractor. Potential teaming partner on large DoD opportunities.",
        ),
        Account(
            id=generate_id(),
            name="Leidos",
            account_type="prime_contractor",
            parent_agency=None,
            office=None,
            location="Reston, VA",
            website="https://www.leidos.com",
            notes="Large prime contractor with strong DHS presence.",
        ),
        Account(
            id=generate_id(),
            name="CyberDefense Solutions LLC",
            account_type="subcontractor",
            parent_agency=None,
            office=None,
            location="Columbia, MD",
            notes="Niche cybersecurity sub. Strong past performance in penetration testing.",
        ),
        Account(
            id=generate_id(),
            name="NASA",
            account_type="government_agency",
            parent_agency=None,
            office="Office of the CIO",
            location="Washington, DC",
            website="https://www.nasa.gov",
            notes="Emerging opportunity for cloud security.",
        ),
    ]


def get_seed_vehicles():
    """Return seed data for contract vehicles"""
    base_date = datetime.now(timezone.utc)
    return [
        ContractVehicle(
            id=generate_id(),
            name="GSA Multiple Award Schedule (MAS)",
            agency="General Services Administration",
            contract_number="GS-35F-0001A",
            expiration_date=base_date + timedelta(days=730),
            ceiling_value=500000000,
            prime_or_sub="prime",
            notes="IT Schedule 70 / MAS consolidation. Covers IT services and solutions.",
        ),
        ContractVehicle(
            id=generate_id(),
            name="OASIS SB Pool 1",
            agency="General Services Administration",
            contract_number="GS00Q14OADS100",
            expiration_date=base_date + timedelta(days=1095),
            ceiling_value=60000000000,
            prime_or_sub="prime",
            notes="Best-in-Class vehicle for complex professional services.",
        ),
        ContractVehicle(
            id=generate_id(),
            name="SeaPort-NxG",
            agency="Department of the Navy",
            contract_number="N00178-19-D-0001",
            expiration_date=base_date + timedelta(days=1825),
            ceiling_value=None,
            prime_or_sub="sub",
            notes="Navy IDIQ for engineering, technical and programmatic support.",
        ),
    ]


def get_seed_opportunities(accounts, vehicles, user_id):
    """Return seed data for opportunities"""
    base_date = datetime.now(timezone.utc)
    dod = accounts[0]
    gsa = accounts[1]
    dhs = accounts[2]
    nasa = accounts[6]

    opps = [
        Opportunity(
            id=generate_id(),
            title="DoD Zero Trust Architecture Implementation",
            agency="Department of Defense",
            account_id=dod.id,
            naics_code="541512",
            set_aside_type="small_business",
            estimated_value=25000000,
            solicitation_number="W15QKN-24-R-0042",
            source="sam_gov",
            stage="capture",
            capture_manager_id=user_id,
            expected_release_date=base_date + timedelta(days=30),
            proposal_due_date=base_date + timedelta(days=60),
            award_date_estimate=base_date + timedelta(days=120),
            win_probability=45,
            notes="Zero Trust implementation across DoD networks. Key focus area for FY25.",
            created_by_user_id=user_id,
        ),
        Opportunity(
            id=generate_id(),
            title="GSA FedRAMP Authorization Support",
            agency="General Services Administration",
            account_id=gsa.id,
            naics_code="541519",
            set_aside_type="8a",
            estimated_value=8500000,
            solicitation_number="GSA-FAS-24-0087",
            source="agency_forecast",
            stage="qualified",
            capture_manager_id=user_id,
            expected_release_date=base_date + timedelta(days=45),
            proposal_due_date=base_date + timedelta(days=90),
            award_date_estimate=base_date + timedelta(days=150),
            win_probability=60,
            notes="FedRAMP package acceleration services. Strong alignment with our platform.",
            created_by_user_id=user_id,
        ),
        Opportunity(
            id=generate_id(),
            title="DHS CISA Cyber Assessment Tools",
            agency="Department of Homeland Security",
            account_id=dhs.id,
            naics_code="541512",
            set_aside_type="full_and_open",
            estimated_value=42000000,
            solicitation_number="70RCSA24R00000015",
            source="sam_gov",
            stage="teaming",
            capture_manager_id=user_id,
            expected_release_date=base_date - timedelta(days=10),
            proposal_due_date=base_date + timedelta(days=40),
            award_date_estimate=base_date + timedelta(days=180),
            win_probability=35,
            notes="Large full & open. Need strong teaming partner. Booz Allen interested.",
            created_by_user_id=user_id,
        ),
        Opportunity(
            id=generate_id(),
            title="NASA Cloud Security Modernization",
            agency="NASA",
            account_id=nasa.id,
            naics_code="541519",
            set_aside_type="small_business",
            estimated_value=12000000,
            solicitation_number="80NSSC24R0001",
            source="partner_referral",
            stage="identified",
            capture_manager_id=user_id,
            expected_release_date=base_date + timedelta(days=90),
            proposal_due_date=None,
            award_date_estimate=base_date + timedelta(days=270),
            win_probability=25,
            notes="Early stage. Referred by CyberDefense Solutions.",
            created_by_user_id=user_id,
        ),
        Opportunity(
            id=generate_id(),
            title="DoD Endpoint Detection & Response",
            agency="Department of Defense",
            account_id=dod.id,
            naics_code="541512",
            set_aside_type="small_business",
            estimated_value=18000000,
            solicitation_number="W911QX-23-R-0055",
            source="incumbent_recompete",
            stage="proposal",
            capture_manager_id=user_id,
            expected_release_date=base_date - timedelta(days=30),
            proposal_due_date=base_date + timedelta(days=14),
            award_date_estimate=base_date + timedelta(days=90),
            win_probability=55,
            notes="Recompete of existing EDR contract. We are the incumbent.",
            created_by_user_id=user_id,
        ),
        Opportunity(
            id=generate_id(),
            title="GSA IT Professional Services BPA",
            agency="General Services Administration",
            account_id=gsa.id,
            naics_code="541511",
            set_aside_type="wosb",
            estimated_value=5000000,
            solicitation_number=None,
            source="internal",
            stage="awarded",
            capture_manager_id=user_id,
            expected_release_date=base_date - timedelta(days=180),
            proposal_due_date=base_date - timedelta(days=120),
            award_date_estimate=base_date - timedelta(days=30),
            win_probability=100,
            notes="Won! BPA for IT professional services. 3 year base + 2 option years.",
            created_by_user_id=user_id,
        ),
    ]

    # Link vehicles to opportunities
    if vehicles:
        opps[0].vehicles = [vehicles[1]]  # OASIS
        opps[1].vehicles = [vehicles[0]]  # GSA MAS
        opps[4].vehicles = [vehicles[1]]  # OASIS

    return opps


def get_seed_teaming(opportunities, accounts):
    """Return seed data for teaming relationships"""
    booz = accounts[3]
    leidos = accounts[4]
    cyber_def = accounts[5]

    return [
        Teaming(
            id=generate_id(),
            opportunity_id=opportunities[2].id,  # DHS CISA
            partner_account_id=booz.id,
            role="prime",
            status="nda_signed",
            notes="Booz Allen as prime, we sub on cyber assessment tools.",
        ),
        Teaming(
            id=generate_id(),
            opportunity_id=opportunities[2].id,  # DHS CISA
            partner_account_id=cyber_def.id,
            role="subcontractor",
            status="potential",
            notes="CyberDefense for penetration testing scope.",
        ),
        Teaming(
            id=generate_id(),
            opportunity_id=opportunities[0].id,  # DoD Zero Trust
            partner_account_id=leidos.id,
            role="subcontractor",
            status="teaming_agreed",
            notes="Leidos subcontracting network engineering scope to us.",
        ),
    ]


def get_seed_proposals(opportunities, user_id):
    """Return seed data for proposals"""
    base_date = datetime.now(timezone.utc)

    return [
        Proposal(
            id=generate_id(),
            opportunity_id=opportunities[4].id,  # DoD EDR (proposal stage)
            proposal_manager_id=user_id,
            submission_type="full",
            submission_deadline=base_date + timedelta(days=14),
            status="in_progress",
            notes="Technical volume 60% complete. Pricing due next week.",
        ),
    ]


def get_seed_compliance():
    """Return seed data for compliance certifications"""
    base_date = datetime.now(timezone.utc)

    return [
        Compliance(
            id=generate_id(),
            certification_type="small_business",
            issued_by="U.S. Small Business Administration",
            issue_date=base_date - timedelta(days=365),
            expiration_date=base_date + timedelta(days=730),
            status="active",
            notes="Small business certification. Annual review required.",
        ),
        Compliance(
            id=generate_id(),
            certification_type="8a",
            issued_by="U.S. Small Business Administration",
            issue_date=base_date - timedelta(days=1000),
            expiration_date=base_date + timedelta(days=95),
            status="expiring_soon",
            notes="8(a) certification expiring in ~3 months. Begin renewal process.",
        ),
        Compliance(
            id=generate_id(),
            certification_type="sdvosb",
            issued_by="Department of Veterans Affairs",
            issue_date=base_date - timedelta(days=200),
            expiration_date=base_date + timedelta(days=530),
            status="active",
            notes="Service-Disabled Veteran-Owned Small Business certification.",
        ),
    ]


def seed_database(db):
    """Seed the database with initial data.

    Runs automatically in development. In other environments, set
    SEED_DEMO_DATA=true to opt in.
    """
    env = os.getenv("ENV", "development")
    seed_flag = os.getenv("SEED_DEMO_DATA", "").lower() in ("true", "1", "yes")
    if env != "development" and not seed_flag:
        logger.info("Skipping database seeding in %s environment", env)
        return

    # Check if data already exists
    existing_user = db.query(User).first()
    if existing_user:
        logger.info("Database already seeded. Skipping...")
        return

    logger.info("Seeding database...")

    # Add user
    user = get_seed_user()
    db.add(user)
    db.flush()

    # Add accounts
    accounts = get_seed_accounts()
    for account in accounts:
        db.add(account)
    db.flush()

    # Add contacts (link some to accounts)
    contacts = get_seed_contacts(user.id)
    # Link government contacts to their agency accounts
    contacts[0].account_id = accounts[0].id  # Sarah -> DoD
    contacts[2].account_id = accounts[1].id  # Emily -> GSA
    contacts[4].account_id = accounts[2].id  # Jennifer -> DHS
    for contact in contacts:
        db.add(contact)
    db.flush()

    # Add communications
    communications = get_seed_communications(contacts)
    for communication in communications:
        db.add(communication)

    # Add contracts (legacy)
    contracts = get_seed_contracts(contacts)
    for contract in contracts:
        db.add(contract)

    # Add contract vehicles
    vehicles = get_seed_vehicles()
    for vehicle in vehicles:
        db.add(vehicle)
    db.flush()

    # Add opportunities
    opportunities = get_seed_opportunities(accounts, vehicles, user.id)
    for opp in opportunities:
        db.add(opp)
    db.flush()

    # Add teaming records
    teaming_records = get_seed_teaming(opportunities, accounts)
    for teaming in teaming_records:
        db.add(teaming)

    # Add proposals
    proposals = get_seed_proposals(opportunities, user.id)
    for proposal in proposals:
        db.add(proposal)

    # Add compliance records
    compliance_records = get_seed_compliance()
    for record in compliance_records:
        db.add(record)

    db.commit()
    logger.info("Database seeded successfully!")
    logger.warning(
        "Demo admin account seeded: %s / demo1234. "
        "Change this password immediately in any non-development environment!",
        user.email,
    )
