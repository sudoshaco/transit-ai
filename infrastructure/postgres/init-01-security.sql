-- Runs on first init. Die App benutzt POSTGRES_USER (aus .env). Dieser User ist
-- der Owner der DB, aber wir entziehen globale Rechte und setzen sinnvolle
-- Standards. SCRAM-SHA-256 ist in Postgres 16 Default — wir erzwingen es nochmal.

ALTER SYSTEM SET password_encryption = 'scram-sha-256';

-- Nur Authentifizierte Verbindungen aus dem Docker-Netz, keine 'trust'
-- (pg_hba wird separat gemountet über init-02).

-- Logging für Forensik
ALTER SYSTEM SET log_connections = 'on';
ALTER SYSTEM SET log_disconnections = 'on';
ALTER SYSTEM SET log_statement = 'ddl';
ALTER SYSTEM SET log_min_duration_statement = 2000;
ALTER SYSTEM SET log_error_verbosity = 'default';
ALTER SYSTEM SET log_line_prefix = '%t [%p] %q%u@%d from %h ';

-- Statement-Timeout: killt runaway queries
ALTER SYSTEM SET statement_timeout = '30s';
ALTER SYSTEM SET idle_in_transaction_session_timeout = '60s';

-- Verbindungslimits
ALTER SYSTEM SET max_connections = 100;

-- SSL in der Zukunft (wenn Zertifikate montiert)
-- ALTER SYSTEM SET ssl = on;

SELECT pg_reload_conf();

-- Extensions für die App
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

-- Den Owner der DB zwingen, keine Rechte an PUBLIC zu vererben
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO CURRENT_USER;

-- DB-spezifische Defaults
DO $$
DECLARE db TEXT := current_database();
BEGIN
  EXECUTE format('ALTER DATABASE %I SET log_statement = ''ddl''', db);
  EXECUTE format('ALTER DATABASE %I SET statement_timeout = ''30s''', db);
END$$;
