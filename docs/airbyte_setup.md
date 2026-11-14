# 🚀 Airbyte Ingestion Guide: GitHub REST API to Snowflake RAW

This guide explains how Airbyte is integrated into this project's modern ETL architecture.

---

## Architecture Flow

```
┌──────────────────┐       ┌────────────────────────┐       ┌────────────────────────┐
│  GitHub REST API │ ----> │  Airbyte Sync Engine   │ ----> │ Snowflake:             │
│  (Source)        │       │  (Connection & Streams)│       │ GITHUB_ANALYTICS.RAW   │
└──────────────────┘       └────────────────────────┘       └────────────────────────┘
```

---

## 1. Quick Setup via `abctl` (Official Airbyte CLI)

To launch the Airbyte managed service locally:

```bash
# 1. Install Airbyte CLI (abctl)
curl -LsfS https://get.airbyte.com | bash

# 2. Start local Airbyte instance (runs on http://localhost:8000)
abctl local install

# 3. Retrieve default credentials
abctl local credentials
```

---

## 2. Configure Source: GitHub

1. In Airbyte UI (`http://localhost:8000`), click **Sources** ➔ **+ New Source**.
2. Select **GitHub**.
3. Fill in the connection settings:
   - **Personal Access Token**: `${GITHUB_TOKEN}` (from `.env`)
   - **Repositories**:
     ```text
     apache/airflow
     tensorflow/tensorflow
     facebook/react
     rust-lang/rust
     golang/go
     ```
   - **Start Date**: `2025-08-01T00:00:00Z`

---

## 3. Configure Destination: Snowflake

1. Click **Destinations** ➔ **+ New Destination**.
2. Select **Snowflake**.
3. Fill in the connection settings:
   - **Host**: `IWQNQNR-IJ38491.snowflakecomputing.com`
   - **Role**: `INGEST_ROLE`
   - **Warehouse**: `GH_WH`
   - **Database**: `GITHUB_ANALYTICS`
   - **Default Schema**: `RAW`
   - **Username**: `SVC_INGEST`
   - **Authentication**: Key-Pair Authentication
   - **Private Key**: Contents of `rsa_key.p8`

---

## 4. Connection & Sync Configuration

1. Connect the GitHub Source to the Snowflake Destination.
2. Select streams:
   - `repositories`
   - `commits`
   - `issues`
   - `pull_requests`
3. Set Sync Mode: **Incremental Append + Deduped** (or **Incremental Append**).
4. Frequency: **Manual** (triggered automatically by Apache Airflow DAG or on-demand).

---

## 5. Airflow + Airbyte Integration

In `orchestration/dags/github_pipeline_dag.py`, Airbyte can be triggered using the `AirbyteTriggerSyncOperator`:

```python
from airflow.providers.airbyte.operators.airbyte import AirbyteTriggerSyncOperator

trigger_airbyte_sync = AirbyteTriggerSyncOperator(
    task_id='trigger_airbyte_sync',
    airbyte_conn_id='airbyte_default',
    connection_id='<AIRBYTE_CONNECTION_ID>',
    asynchronous=False,
    timeout=3600,
    wait_seconds=10
)
```
