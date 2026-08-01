-- GATE-02: new-stack databases and runtime roles only (no legacy DB).
-- Executed once on first Postgres container start by docker-entrypoint-initdb.d.

CREATE ROLE pricecomp_app LOGIN PASSWORD 'pricecomp_app_dev';
CREATE ROLE pricecomp_phoenix LOGIN PASSWORD 'pricecomp_phoenix_dev';

CREATE DATABASE pricecomp_app;
CREATE DATABASE pricecomp_phoenix OWNER pricecomp_phoenix;

REVOKE ALL ON DATABASE pricecomp_app FROM PUBLIC;
REVOKE ALL ON DATABASE pricecomp_phoenix FROM PUBLIC;

GRANT CONNECT ON DATABASE pricecomp_app TO pricecomp_app;
GRANT CONNECT ON DATABASE pricecomp_phoenix TO pricecomp_phoenix;

\c pricecomp_app

GRANT USAGE ON SCHEMA public TO pricecomp_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO pricecomp_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO pricecomp_app;

\c pricecomp_phoenix

GRANT ALL ON SCHEMA public TO pricecomp_phoenix;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON TABLES TO pricecomp_phoenix;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON SEQUENCES TO pricecomp_phoenix;
