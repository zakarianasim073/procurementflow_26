-- Executed only when PostgreSQL initializes a new empty data directory.
-- Application schema changes remain exclusively managed by Alembic.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
