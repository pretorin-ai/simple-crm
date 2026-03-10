"""Tests for seed data module."""

from unittest.mock import patch

from app.seed_data import (
    generate_id,
    get_seed_communications,
    get_seed_contacts,
    get_seed_contracts,
    get_seed_user,
    seed_database,
)


def test_generate_id():
    id1 = generate_id()
    id2 = generate_id()
    assert isinstance(id1, str)
    assert id1 != id2
    assert len(id1) == 36  # UUID format


def test_get_seed_user():
    user = get_seed_user()
    assert user.email == "demo@pretorin.com"
    assert user.role == "admin"
    assert user.is_active is True
    assert user.name == "Demo Admin User"


def test_get_seed_contacts():
    contacts = get_seed_contacts("user-id-123")
    assert len(contacts) == 5
    assert contacts[0].first_name == "Sarah"
    assert contacts[0].assigned_user_id == "user-id-123"
    for c in contacts:
        assert c.assigned_user_id == "user-id-123"


def test_get_seed_communications():
    contacts = get_seed_contacts("user-id-123")
    comms = get_seed_communications(contacts)
    assert len(comms) == 4
    # First two should be for Sarah's contact_id
    assert comms[0].contact_id == contacts[0].id
    assert comms[1].contact_id == contacts[0].id


def test_get_seed_communications_empty_contacts():
    comms = get_seed_communications([])
    assert len(comms) == 4  # Still creates them with generated IDs


def test_get_seed_contracts():
    contacts = get_seed_contacts("user-id-123")
    contracts = get_seed_contracts(contacts)
    assert len(contracts) == 4
    assert contracts[0].title == "DoD Cybersecurity Compliance Automation"
    assert len(contracts[0].assigned_contacts) == 1


def test_get_seed_contracts_empty_contacts():
    contracts = get_seed_contracts([])
    assert len(contracts) == 4
    assert contracts[0].assigned_contacts == []


@patch.dict("os.environ", {"ENV": "development"})
def test_seed_database_fresh(db):
    seed_database(db)
    from app.models.models import Communication, Contact, Contract, User

    assert db.query(User).count() == 1
    assert db.query(Contact).count() == 5
    assert db.query(Communication).count() == 4
    assert db.query(Contract).count() == 4


@patch.dict("os.environ", {"ENV": "development"})
def test_seed_database_already_seeded(db):
    """Seeding twice should not duplicate data."""
    seed_database(db)
    seed_database(db)
    from app.models.models import User

    assert db.query(User).count() == 1


@patch.dict("os.environ", {"ENV": "production", "SEED_DEMO_DATA": ""})
def test_seed_database_skipped_in_production(db):
    """Seeding should be skipped in non-development environments."""
    seed_database(db)
    from app.models.models import User

    assert db.query(User).count() == 0


@patch.dict("os.environ", {"ENV": "production", "SEED_DEMO_DATA": "true"})
def test_seed_database_production_with_flag(db):
    """SEED_DEMO_DATA=true overrides the environment check."""
    seed_database(db)
    from app.models.models import User

    assert db.query(User).count() == 1


@patch.dict("os.environ", {"ENV": "production", "SEED_DEMO_DATA": "false"})
def test_seed_database_production_flag_false(db):
    """SEED_DEMO_DATA=false does not seed."""
    seed_database(db)
    from app.models.models import User

    assert db.query(User).count() == 0
