-- =============================================================================
-- snowflake/00_setup.sql
-- Run this ONCE as ACCOUNTADMIN in a Snowflake worksheet.
-- Replace <YOUR_SNOWFLAKE_USER> with your personal Snowflake login.
-- =============================================================================

USE ROLE ACCOUNTADMIN;

-- ── Warehouse ─────────────────────────────────────────────────────────────────
CREATE WAREHOUSE IF NOT EXISTS GH_WH
    WAREHOUSE_SIZE   = 'XSMALL'
    AUTO_SUSPEND     = 60          -- suspends after 60 s of inactivity
    AUTO_RESUME      = TRUE
    INITIALLY_SUSPENDED = TRUE;   -- don't burn credits until first query

-- ── Database & schemas ────────────────────────────────────────────────────────
CREATE DATABASE IF NOT EXISTS GITHUB_ANALYTICS;
CREATE SCHEMA IF NOT EXISTS GITHUB_ANALYTICS.RAW;

-- ── Roles ─────────────────────────────────────────────────────────────────────
CREATE ROLE IF NOT EXISTS INGEST_ROLE;
CREATE ROLE IF NOT EXISTS TRANSFORM_ROLE;
CREATE ROLE IF NOT EXISTS BI_ROLE;

-- Warehouse access
GRANT USAGE ON WAREHOUSE GH_WH TO ROLE INGEST_ROLE;
GRANT USAGE ON WAREHOUSE GH_WH TO ROLE TRANSFORM_ROLE;
GRANT USAGE ON WAREHOUSE GH_WH TO ROLE BI_ROLE;

-- Database access
GRANT USAGE ON DATABASE GITHUB_ANALYTICS TO ROLE INGEST_ROLE;
GRANT USAGE ON DATABASE GITHUB_ANALYTICS TO ROLE TRANSFORM_ROLE;
GRANT USAGE ON DATABASE GITHUB_ANALYTICS TO ROLE BI_ROLE;

-- RAW schema: ingest writes, transform reads
GRANT ALL        ON SCHEMA GITHUB_ANALYTICS.RAW TO ROLE INGEST_ROLE;
GRANT USAGE      ON SCHEMA GITHUB_ANALYTICS.RAW TO ROLE TRANSFORM_ROLE;
GRANT SELECT ON ALL    TABLES IN SCHEMA GITHUB_ANALYTICS.RAW TO ROLE TRANSFORM_ROLE;
GRANT SELECT ON FUTURE TABLES IN SCHEMA GITHUB_ANALYTICS.RAW TO ROLE TRANSFORM_ROLE;

-- dbt needs to create its own schemas (staging, intermediate, marts)
GRANT CREATE SCHEMA ON DATABASE GITHUB_ANALYTICS TO ROLE TRANSFORM_ROLE;

-- ── Service accounts (key-pair auth — no passwords) ───────────────────────────
CREATE USER IF NOT EXISTS SVC_INGEST
    DEFAULT_ROLE      = INGEST_ROLE
    DEFAULT_WAREHOUSE = GH_WH;

CREATE USER IF NOT EXISTS SVC_DBT
    DEFAULT_ROLE      = TRANSFORM_ROLE
    DEFAULT_WAREHOUSE = GH_WH;

GRANT ROLE INGEST_ROLE    TO USER SVC_INGEST;
GRANT ROLE TRANSFORM_ROLE TO USER SVC_DBT;

-- ── Your personal user — so you can query and test locally ────────────────────
-- Replace <YOUR_SNOWFLAKE_USER> with your actual login username
GRANT ROLE INGEST_ROLE    TO USER <YOUR_SNOWFLAKE_USER>;
GRANT ROLE TRANSFORM_ROLE TO USER <YOUR_SNOWFLAKE_USER>;

-- ── Credit guard (20 credits max, alert at 80%, suspend at 100%) ──────────────
CREATE RESOURCE MONITOR IF NOT EXISTS GH_MONITOR
    WITH CREDIT_QUOTA = 20
    TRIGGERS
        ON  80 PERCENT DO NOTIFY
        ON 100 PERCENT DO SUSPEND;

ALTER WAREHOUSE GH_WH SET RESOURCE_MONITOR = GH_MONITOR;

-- =============================================================================
-- After dbt has created the MARTS schema, run these to let Metabase read it:
-- =============================================================================
-- GRANT USAGE  ON SCHEMA GITHUB_ANALYTICS.MARTS TO ROLE BI_ROLE;
-- GRANT SELECT ON ALL    TABLES IN SCHEMA GITHUB_ANALYTICS.MARTS TO ROLE BI_ROLE;
-- GRANT SELECT ON FUTURE TABLES IN SCHEMA GITHUB_ANALYTICS.MARTS TO ROLE BI_ROLE;

