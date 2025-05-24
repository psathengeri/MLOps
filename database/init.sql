-- Initialize multi-tenant database
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create a function to initialize tenant schema
CREATE OR REPLACE FUNCTION create_tenant_schema(tenant_name TEXT)
RETURNS VOID AS $$
BEGIN
    EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', tenant_name);
    -- Add any tenant-specific tables here
END;
$$ LANGUAGE plpgsql;
