"""add missing index and check constraints

Revision ID: a2b3c4d5e6f7
Revises: c769fd9e5252
Create Date: 2026-03-09 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "c769fd9e5252"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Missing index ---
    op.create_index("ix_contracts_created_by_user_id", "contracts", ["created_by_user_id"])

    # --- CHECK constraints ---
    op.create_check_constraint(
        "ck_accounts_account_type",
        "accounts",
        "account_type IN ("
        "'government_agency','prime_contractor','subcontractor','partner','vendor')",
    )
    op.create_check_constraint(
        "ck_contacts_contact_type",
        "contacts",
        "contact_type IN ('individual','commercial','government')",
    )
    op.create_check_constraint(
        "ck_contacts_status",
        "contacts",
        "status IN ('cold','warm','hot')",
    )
    op.create_check_constraint(
        "ck_communications_type",
        "communications",
        "type IN ('email','phone','meeting','other')",
    )
    op.create_check_constraint(
        "ck_communications_direction",
        "communications",
        "direction IN ('inbound','outbound') OR direction IS NULL",
    )
    op.create_check_constraint(
        "ck_contracts_status",
        "contracts",
        "status IN ('prospective','in progress','submitted','not a good fit')",
    )
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('admin','user')",
    )
    op.create_check_constraint(
        "ck_users_auth_provider",
        "users",
        "auth_provider IN ('local','google') OR auth_provider IS NULL",
    )
    op.create_check_constraint(
        "ck_opportunities_set_aside_type",
        "opportunities",
        "set_aside_type IN ("
        "'small_business','8a','hubzone','wosb','sdvosb','full_and_open','none'"
        ") OR set_aside_type IS NULL",
    )
    op.create_check_constraint(
        "ck_opportunities_source",
        "opportunities",
        "source IN ("
        "'sam_gov','agency_forecast','incumbent_recompete','partner_referral','internal'"
        ") OR source IS NULL",
    )
    op.create_check_constraint(
        "ck_opportunities_stage",
        "opportunities",
        "stage IN ("
        "'identified','qualified','capture','teaming','proposal','submitted','awarded','lost'"
        ")",
    )
    op.create_check_constraint(
        "ck_contract_vehicles_prime_or_sub",
        "contract_vehicles",
        "prime_or_sub IN ('prime','sub') OR prime_or_sub IS NULL",
    )
    op.create_check_constraint(
        "ck_teaming_role",
        "teaming",
        "role IN ('prime','subcontractor','jv_partner')",
    )
    op.create_check_constraint(
        "ck_teaming_status",
        "teaming",
        "status IN ('potential','nda_signed','teaming_agreed','active','inactive')",
    )
    op.create_check_constraint(
        "ck_proposals_submission_type",
        "proposals",
        "submission_type IN ('full','partial','draft') OR submission_type IS NULL",
    )
    op.create_check_constraint(
        "ck_proposals_status",
        "proposals",
        "status IN ('not_started','in_progress','review','final','submitted')",
    )
    op.create_check_constraint(
        "ck_opportunity_events_event_type",
        "opportunity_events",
        "event_type IN ("
        "'discovery','contact','rfp_release','proposal_submitted',"
        "'meeting','stage_change','note','other')",
    )
    op.create_check_constraint(
        "ck_capture_notes_section",
        "capture_notes",
        "section IN ("
        "'customer_intel','incumbent','competitors','partners','risks','strategy')",
    )
    op.create_check_constraint(
        "ck_audit_log_action",
        "audit_log",
        "action IN ('create','update','delete','restore')",
    )
    op.create_check_constraint(
        "ck_compliance_certification_type",
        "compliance",
        "certification_type IN ('small_business','8a','hubzone','wosb','sdvosb','edwosb')",
    )
    op.create_check_constraint(
        "ck_compliance_status",
        "compliance",
        "status IN ('active','expiring_soon','expired','pending')",
    )


def downgrade() -> None:
    # --- Remove CHECK constraints ---
    op.drop_constraint("ck_compliance_status", "compliance", type_="check")
    op.drop_constraint("ck_compliance_certification_type", "compliance", type_="check")
    op.drop_constraint("ck_audit_log_action", "audit_log", type_="check")
    op.drop_constraint("ck_capture_notes_section", "capture_notes", type_="check")
    op.drop_constraint("ck_opportunity_events_event_type", "opportunity_events", type_="check")
    op.drop_constraint("ck_proposals_status", "proposals", type_="check")
    op.drop_constraint("ck_proposals_submission_type", "proposals", type_="check")
    op.drop_constraint("ck_teaming_status", "teaming", type_="check")
    op.drop_constraint("ck_teaming_role", "teaming", type_="check")
    op.drop_constraint("ck_contract_vehicles_prime_or_sub", "contract_vehicles", type_="check")
    op.drop_constraint("ck_opportunities_stage", "opportunities", type_="check")
    op.drop_constraint("ck_opportunities_source", "opportunities", type_="check")
    op.drop_constraint("ck_opportunities_set_aside_type", "opportunities", type_="check")
    op.drop_constraint("ck_users_auth_provider", "users", type_="check")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_constraint("ck_contracts_status", "contracts", type_="check")
    op.drop_constraint("ck_communications_direction", "communications", type_="check")
    op.drop_constraint("ck_communications_type", "communications", type_="check")
    op.drop_constraint("ck_contacts_status", "contacts", type_="check")
    op.drop_constraint("ck_contacts_contact_type", "contacts", type_="check")
    op.drop_constraint("ck_accounts_account_type", "accounts", type_="check")

    # --- Remove index ---
    op.drop_index("ix_contracts_created_by_user_id", "contracts")
