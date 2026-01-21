-- Migration: Add queue fields for action queue feature
-- This migration adds columns to support:
-- 1. Tracking API-created items that need to be claimed
-- 2. Tracking contact reassignments that need acceptance

-- Contact table: Add queue-related columns
ALTER TABLE contacts ADD COLUMN created_via VARCHAR(50) NOT NULL DEFAULT 'user';
ALTER TABLE contacts ADD COLUMN is_claimed BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE contacts ADD COLUMN pending_acceptance BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE contacts ADD COLUMN reassigned_by_user_id VARCHAR(255) REFERENCES users(id);

-- Contract table: Add queue-related columns
ALTER TABLE contracts ADD COLUMN created_via VARCHAR(50) NOT NULL DEFAULT 'user';
ALTER TABLE contracts ADD COLUMN is_claimed BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE contracts ADD COLUMN claimed_by_user_id VARCHAR(255) REFERENCES users(id);

-- Create indexes for efficient querying
CREATE INDEX idx_contacts_is_claimed ON contacts(is_claimed);
CREATE INDEX idx_contacts_pending_acceptance ON contacts(pending_acceptance);
CREATE INDEX idx_contacts_created_via ON contacts(created_via);
CREATE INDEX idx_contracts_is_claimed ON contracts(is_claimed);
CREATE INDEX idx_contracts_created_via ON contracts(created_via);
