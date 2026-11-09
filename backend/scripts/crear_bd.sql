-- Ejecutar como superusuario:
--   psql -U postgres -h localhost -f scripts/crear_bd.sql
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'talentflow_app') THEN
    CREATE ROLE talentflow_app LOGIN PASSWORD 'talentflow_pass';
  END IF;
END $$;

SELECT 'CREATE DATABASE talentflow OWNER talentflow_app ENCODING ''UTF8'' TEMPLATE template0'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'talentflow')\gexec

\c talentflow
-- unaccent es "trusted" desde PG13, pero se crea aquí para no depender de ello.
CREATE EXTENSION IF NOT EXISTS unaccent;
