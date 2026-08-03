-- GATE-02: new-stack databases and runtime roles only (no legacy DB).
-- Executed once on first Postgres container start by docker-entrypoint-initdb.d.

CREATE ROLE agentic_cataloger_app LOGIN PASSWORD 'agentic_cataloger_app_dev';
CREATE ROLE agentic_cataloger_phoenix LOGIN PASSWORD 'agentic_cataloger_phoenix_dev';

CREATE DATABASE agentic_cataloger_app;
CREATE DATABASE agentic_cataloger_phoenix OWNER agentic_cataloger_phoenix;

REVOKE ALL ON DATABASE agentic_cataloger_app FROM PUBLIC;
REVOKE ALL ON DATABASE agentic_cataloger_phoenix FROM PUBLIC;

GRANT CONNECT ON DATABASE agentic_cataloger_app TO agentic_cataloger_app;
GRANT CONNECT ON DATABASE agentic_cataloger_phoenix TO agentic_cataloger_phoenix;

\c agentic_cataloger_app

GRANT USAGE ON SCHEMA public TO agentic_cataloger_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO agentic_cataloger_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO agentic_cataloger_app;

\c agentic_cataloger_phoenix

GRANT ALL ON SCHEMA public TO agentic_cataloger_phoenix;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON TABLES TO agentic_cataloger_phoenix;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON SEQUENCES TO agentic_cataloger_phoenix;
