# 🚀 GitHub Developer Ecosystem Analytics
### Enterprise-Style Modern Data Engineering Pipeline & Conversational BI

Designed and implemented in accordance with enterprise data engineering standards:
Automated ELT process integrating **Apache Airflow**, **Fivetran / Airbyte**, **Snowflake**, **dbt Core**, and an interactive **Conversational BI Interface**.

---

## 1. 🏗️ Architecture & Tech Stack

```
┌──────────────────┐       ┌────────────────────────┐       ┌────────────────────────┐
│  GitHub REST API │ ----> │   Fivetran / Airbyte   │ ----> │  Snowflake Warehouse   │
│  (Source Data)   │       │   (Managed Ingestion)  │       │  (RAW Schema)          │
└──────────────────┘       └────────────────────────┘       └───────────┬────────────┘
                                                                        │
                                                                        ▼
┌──────────────────────────────┐                            ┌────────────────────────┐
│  Conversational BI Interface │ <───────────────────────── │  dbt Transformations   │
│  (Streamlit + Plotly Charts) │   (Data Marts Analytics)   │  (Staging -> Marts)    │
└──────────────────────────────┘                            └────────────────────────┘
               ▲
               │ Orchestrated & Scheduled End-to-End
┌──────────────┴───────────────┐
│        Apache Airflow        │
│   (DAG Pipeline Scheduler)   │
└──────────────────────────────┘
```

| Layer | Technology | Role in Architecture |
|---|---|---|
| **Orchestration** | **Apache Airflow** | Schedules and monitors the automated DAG workflow daily (`github_pipeline_dag.py`) |
| **Data Ingestion** | **Fivetran / Airbyte** | Automated incremental data extraction and loading into Snowflake `RAW` schema |
| **Data Warehouse** | **Snowflake** | Multi-cluster cloud data warehouse (`GITHUB_ANALYTICS`, Warehouse `GH_WH`) |
| **Transformations**| **dbt Core (dbt-snowflake)** | Modular SQL transformations across Staging, Intermediate, and Marts layers |
| **BI / Interface** | **Conversational BI** | Interactive conversational query interface with automated charts (`bi/app.py`) |

---

## 2. ⚡ Implementation Details

### A. Data Ingestion (Fivetran / Airbyte & Ingestion Engine)
- **Source**: GitHub REST API (v2022-11-28).
- **Target Repositories**: `apache/airflow`, `tensorflow/tensorflow`, `facebook/react`, `rust-lang/rust`, `golang/go` (plus dynamic user-submitted repos).
- **Entities Synced**:
  - `REPOSITORIES` (Metadata, stars, forks, open issues count)
  - `REPO_LANGUAGES` (Language byte breakdown per repo)
  - `COMMITS` (Commit hash, author login, timestamp, message)
  - `ISSUES` (Issue id, state, resolution timestamps)
  - `PULL_REQUESTS` (PR id, additions, deletions, merge status)
- **Security**: Asymmetric 2048-bit RSA Key-Pair authentication (`SVC_INGEST`).
- **Setup Guide**: See [`docs/fivetran_setup.md`](docs/fivetran_setup.md) and [`docs/airbyte_setup.md`](docs/airbyte_setup.md).

### B. Orchestration (Apache Airflow)
- **DAG File**: [`orchestration/dags/github_pipeline_dag.py`](orchestration/dags/github_pipeline_dag.py)
- **Execution Workflow**:
  ```text
  [Ingest Task (Fivetran/Airbyte Sync)] ➔ [dbt deps] ➔ [dbt run] ➔ [dbt test]
  ```
- **Features**: Automatic retries, execution timeout guards, SLA alerts, and dependency chaining.

### C. Transformations (dbt Core)
- **Staging Layer** (`dbt_project/models/staging/`): Extracts structured fields from raw JSON payloads (`VARIANT`), deduplicating with `QUALIFY row_number() over (partition by id order by loaded_at desc) = 1`.
- **Intermediate Layer** (`dbt_project/models/intermediate/`):
  - `int_commits_by_repo_month`: Monthly commit volume and distinct contributor counts.
  - `int_issue_resolution`: Issue cycle times, median resolution hours, and close rates.
  - `int_pr_lifecycle`: PR merge velocities and code turnover statistics.
- **Data Marts Layer** (`dbt_project/models/marts/`):
  - `mart_language_activity`: Directly answers *"Which programming languages have the most active repositories?"*
  - `mart_developer_activity`: Contributor leaderboard and cross-project activity.
  - `mart_issue_resolution`: Project health and issue response times.

### D. Conversational BI Query Interface
- **App File**: [`bi/app.py`](bi/app.py)
- **Capabilities**:
  - Natural language questions translated into live Snowflake analytics.
  - Generates interactive Plotly bar charts, scatter plots, and data tables.
  - **Dynamic Ingestion Feature**: Enter any public GitHub repository (e.g., `vuejs/vue`) from the sidebar to immediately ingest and analyze it.

---

## 3. 🚀 Quick Start Guide

### 1. Environment Setup
```powershell
# Activate Python Virtual Environment
.venv\Scripts\activate

# Verify Connectivity to GitHub API and Snowflake
python scripts/test_connections.py
```

### 2. Run the Conversational BI Interface
```powershell
streamlit run bi/app.py
```
Open **`http://localhost:8501`** in your browser to interact with the BI assistant!

### 3. Run dbt Transformations
```powershell
cd dbt_project
dbt deps
dbt build --target dev
```
