-- Migration: Add google_id column and update auth_provider
-- Run this migration to switch from Microsoft Entra ID to Google OAuth

-- Add new google_id column to users table
ALTER TABLE users ADD COLUMN google_id VARCHAR;

-- Create unique index on google_id
CREATE UNIQUE INDEX ix_users_google_id ON users(google_id);

-- Update existing users with entra_id auth_provider to google
-- (They will need to re-authenticate to link their Google account)
UPDATE users SET auth_provider = 'google' WHERE auth_provider = 'entra_id';

-- Note: SQLite doesn't easily drop columns, so entra_object_id will remain but be unused.
-- The column can be cleaned up later if migrating to PostgreSQL or another database.
