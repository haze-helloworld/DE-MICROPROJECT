# 🚀 Fivetran Ingestion Guide: GitHub REST API to Snowflake

This project uses **Fivetran** as the enterprise-grade automated data ingestion engine to extract data from GitHub's REST API and load it continuously into Snowflake.

---

## 🏗️ Architecture Flow

```
┌──────────────────┐       ┌────────────────────────┐       ┌────────────────────────┐
│  GitHub REST API │ ----> │   Fivetran Connector   │ ----> │ Snowflake:             │
│  (Source)        │       │   (Managed Sync)       │       │ GITHUB_ANALYTICS.RAW   │
└──────────────────┘       └────────────────────────┘       └────────────────────────┘
```

---

## 1. Destination Configuration (Snowflake)

In the Fivetran dashboard:
1. Navigate to **Destinations** ➔ Select **Snowflake**.
2. Fill in the connection credentials:
   - **Host**: `IWQNQNR-IJ38491.snowflakecomputing.com`
   - **Port**: `443`
   - **Database**: `GITHUB_ANALYTICS`
   - **Auth Method**: Key Pair
   - **User**: `SVC_INGEST`
   - **Private Key**: Extracted from `rsa_key.p8`
   - **Role**: `INGEST_ROLE`

---

## 2. Source Configuration (GitHub)

1. Navigate to **Connectors** ➔ Select **GitHub**.
2. **Authentication Method**: Personal Access Token (`GITHUB_TOKEN` from `.env`).
3. **Tracked Repositories**:
   ```text
   apache/airflow
   tensorflow/tensorflow
   facebook/react
   rust-lang/rust
   golang/go
   ```
4. **Streams Synced**:
   - `repository`
   - `commit`
   - `issue`
   - `pull_request`

---

## 3. Sync & Transformation Trigger

- Fivetran handles schema drift, deduplication, and automatic incremental loading.
- Transformations can be triggered directly in downstream dbt Core models (`dbt_project/`).
