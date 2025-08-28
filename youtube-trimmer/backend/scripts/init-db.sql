-- Initialization script for PostgreSQL database
-- This script is run when the PostgreSQL container starts for the first time

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set timezone
SET timezone = 'UTC';

-- Create indexes for better performance (will be created by SQLAlchemy, but good to have)
-- These will only be created after the tables exist

-- Note: The actual table creation is handled by SQLAlchemy in the application
-- This script only sets up extensions and configurations