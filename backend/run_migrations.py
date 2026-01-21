#!/usr/bin/env python3
"""
Database migration script for the action queue feature.
This script is idempotent - safe to run multiple times.

Usage:
  Local:  python run_migrations.py
  Docker: docker exec -it <container> python run_migrations.py
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./crm.db")


def column_exists(inspector, table_name, column_name):
    """Check if a column exists in a table."""
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def table_exists(inspector, table_name):
    """Check if a table exists."""
    return table_name in inspector.get_table_names()


def run_migrations():
    """Run all pending migrations."""
    print(f"Connecting to database: {DATABASE_URL.split('?')[0]}")
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)

    with engine.connect() as conn:
        # Migration: Add queue fields to contacts table
        print("\n=== Checking contacts table ===")

        if not column_exists(inspector, 'contacts', 'created_via'):
            print("Adding created_via column to contacts...")
            conn.execute(text("ALTER TABLE contacts ADD COLUMN created_via VARCHAR(50) NOT NULL DEFAULT 'user'"))
        else:
            print("created_via column already exists")

        if not column_exists(inspector, 'contacts', 'is_claimed'):
            print("Adding is_claimed column to contacts...")
            conn.execute(text("ALTER TABLE contacts ADD COLUMN is_claimed BOOLEAN NOT NULL DEFAULT 1"))
        else:
            print("is_claimed column already exists")

        if not column_exists(inspector, 'contacts', 'pending_acceptance'):
            print("Adding pending_acceptance column to contacts...")
            conn.execute(text("ALTER TABLE contacts ADD COLUMN pending_acceptance BOOLEAN NOT NULL DEFAULT 0"))
        else:
            print("pending_acceptance column already exists")

        if not column_exists(inspector, 'contacts', 'reassigned_by_user_id'):
            print("Adding reassigned_by_user_id column to contacts...")
            conn.execute(text("ALTER TABLE contacts ADD COLUMN reassigned_by_user_id VARCHAR(255)"))
        else:
            print("reassigned_by_user_id column already exists")

        # Migration: Add queue fields to contracts table
        print("\n=== Checking contracts table ===")

        if not column_exists(inspector, 'contracts', 'created_via'):
            print("Adding created_via column to contracts...")
            conn.execute(text("ALTER TABLE contracts ADD COLUMN created_via VARCHAR(50) NOT NULL DEFAULT 'user'"))
        else:
            print("created_via column already exists")

        if not column_exists(inspector, 'contracts', 'is_claimed'):
            print("Adding is_claimed column to contracts...")
            conn.execute(text("ALTER TABLE contracts ADD COLUMN is_claimed BOOLEAN NOT NULL DEFAULT 1"))
        else:
            print("is_claimed column already exists")

        if not column_exists(inspector, 'contracts', 'claimed_by_user_id'):
            print("Adding claimed_by_user_id column to contracts...")
            conn.execute(text("ALTER TABLE contracts ADD COLUMN claimed_by_user_id VARCHAR(255)"))
        else:
            print("claimed_by_user_id column already exists")

        # Migration: Create contract_acknowledgments table
        print("\n=== Checking contract_acknowledgments table ===")

        if not table_exists(inspector, 'contract_acknowledgments'):
            print("Creating contract_acknowledgments table...")
            conn.execute(text("""
                CREATE TABLE contract_acknowledgments (
                    contract_id VARCHAR NOT NULL,
                    user_id VARCHAR NOT NULL,
                    acknowledged_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (contract_id, user_id),
                    FOREIGN KEY (contract_id) REFERENCES contracts(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """))
        else:
            print("contract_acknowledgments table already exists")

        conn.commit()
        print("\n=== Migration completed successfully ===")


if __name__ == "__main__":
    try:
        run_migrations()
    except Exception as e:
        print(f"Migration failed: {e}", file=sys.stderr)
        sys.exit(1)
