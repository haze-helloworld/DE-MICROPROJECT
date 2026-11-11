# GitHub Developer Ecosystem Analytics

A data engineering pipeline that tracks GitHub activity across popular repositories, answers the question **"Which programming languages have the most active developer communities?"**, and surfaces the results in a Metabase dashboard.

## Architecture

```
GitHub REST API → Python extractor → Snowflake RAW → dbt → MARTS → Metabase
                                              ↑
                                    GitHub Actions (daily cron)
```

## Team

| Owner | Scope |
|-------|-------|
| **Tanvi** | Snowflake setup, ingestion, orchestration, CI/CD |
| **Riya** | dbt models (staging → intermediate → marts), data quality, dashboard |

## Repo layout

```
.env.example                  ← copy to .env, fill in secrets
requirements.txt
docker-compose.yml            ← Metabase
ingestion/
  extractor.py                ← Python GitHub → Snowflake loader
  repos.txt                   ← one owner/repo per line
snowflake/
  00_setup.sql                ← run once as ACCOUNTADMIN
dbt_project/
  dbt_project.yml
  profiles.yml.example        ← copy to ~/.dbt/profiles.yml
  models/
    staging/                  ← parse raw JSON
    intermediate/             ← (Riya) aggregations
    marts/                    ← (Riya) final tables
  macros/
    generate_schema_name.sql
.github/workflows/
  ci.yml                      ← lint + dbt build + daily ingest
docs/
  data_dictionary.md
```

## Quick start (Tanvi's setup)

```bash
# 1. Clone and open workspace
git clone <your-repo-url>
cd github-ecosystem-analytics

# 2. Create virtualenv
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 3. Configure secrets
cp .env.example .env          # fill in GITHUB_TOKEN and Snowflake creds

# 4. Generate Snowflake key-pair
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt
openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub

# 5. Run Snowflake setup (paste 00_setup.sql into a Snowflake worksheet)

# 6. Test GitHub API
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/rate_limit

# 7. Run extractor
python ingestion/extractor.py

# 8. Start Metabase (after Riya's marts exist)
docker compose up -d
# → open http://localhost:3000
```

## GitHub Secrets required

| Secret name | What it is |
|---|---|
| `GH_PAT` | GitHub fine-grained PAT (not `GITHUB_TOKEN` — that's reserved) |
| `SNOWFLAKE_ACCOUNT` | e.g. `orgname-accountname` |
| `SNOWFLAKE_USER` | `SVC_INGEST` |
| `SNOWFLAKE_PRIVATE_KEY` | Contents of `rsa_key.p8` |

