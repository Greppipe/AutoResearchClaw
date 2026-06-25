-- PostgreSQL initialization
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Full-text search configuration
CREATE TEXT SEARCH CONFIGURATION IF NOT EXISTS research_text (COPY = english);
