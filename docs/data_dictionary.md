# Data Dictionary

> Updated by Tanvi after each ingestion change. Riya uses this to write dbt models.

---

## RAW schema tables (Snowflake)

All tables have:
- `payload VARIANT` — raw GitHub API JSON object
- `loaded_at TIMESTAMP_TZ` — when the row was inserted by the extractor

### RAW.REPOSITORIES
One row per API call to `GET /repos/{owner}/{repo}`.

| JSON path | Type | Description |
|---|---|---|
| `payload:id` | number | GitHub numeric repo ID |
| `payload:full_name` | string | `owner/repo` |
| `payload:owner:login` | string | Owner username or org |
| `payload:language` | string | Primary language |
| `payload:stargazers_count` | number | Star count |
| `payload:forks_count` | number | Fork count |
| `payload:open_issues_count` | number | Open issues + open PRs |
| `payload:created_at` | timestamp | Repo creation date |
| `payload:pushed_at` | timestamp | Last push date |

### RAW.REPO_LANGUAGES
One row per repo — the full language-bytes map as JSON.

| JSON path | Type | Description |
|---|---|---|
| `payload:repo` | string | `owner/repo` |
| `payload:languages` | object | `{language: bytes}` map |

### RAW.COMMITS
One row per commit from `GET /repos/{owner}/{repo}/commits?since=...`

| JSON path | Type | Description |
|---|---|---|
| `payload:sha` | string | Commit SHA (unique) |
| `payload:repo` | string | `owner/repo` |
| `payload:commit:author:date` | timestamp | Commit timestamp |
| `payload:commit:author:name` | string | Author display name |
| `payload:commit:author:email` | string | Author email |
| `payload:author:login` | string | GitHub username (may be null) |
| `payload:commit:message` | string | Commit message |

### RAW.ISSUES
Issues AND pull requests from `GET /repos/{owner}/{repo}/issues?state=all`.
Filter `payload:pull_request is null` to get issues only.

| JSON path | Type | Description |
|---|---|---|
| `payload:id` | number | GitHub issue ID |
| `payload:number` | number | Issue number within repo |
| `payload:repo` | string | `owner/repo` |
| `payload:title` | string | Issue title |
| `payload:state` | string | `open` or `closed` |
| `payload:user:login` | string | Author login |
| `payload:created_at` | timestamp | Opened at |
| `payload:closed_at` | timestamp | Closed at (null if open) |
| `payload:pull_request` | object | Non-null for PRs → use to exclude |

### RAW.PULL_REQUESTS
From `GET /repos/{owner}/{repo}/pulls?state=all`.

| JSON path | Type | Description |
|---|---|---|
| `payload:id` | number | GitHub PR ID |
| `payload:number` | number | PR number within repo |
| `payload:repo` | string | `owner/repo` |
| `payload:state` | string | `open` or `closed` |
| `payload:merged` | boolean | Whether merged |
| `payload:draft` | boolean | Whether draft |
| `payload:user:login` | string | Author login |
| `payload:created_at` | timestamp | Opened at |
| `payload:merged_at` | timestamp | Merged at (null if not merged) |
| `payload:additions` | number | Lines added |
| `payload:deletions` | number | Lines removed |
| `payload:changed_files` | number | Files changed |

---

## Staging models (dbt)

Parsed from RAW. One row per entity, deduped to latest load.

| Model | Key column | Description |
|---|---|---|
| `stg_repositories` | `repo_id` | Repo metadata snapshot |
| `stg_repo_languages` | `full_name + language` | Language bytes per repo |
| `stg_commits` | `commit_sha` | Parsed commit records |
| `stg_issues` | `issue_id` | Issues only (no PRs) |
| `stg_pull_requests` | `pr_id` | Pull request records |

---

## Conventions

- Timestamps: always `TIMESTAMP_TZ`
- Repo identifier: always `full_name` (`owner/repo` string)
- "Active" repo: at least one commit in the last 90 days (`pushed_at >= DATEADD(day, -90, CURRENT_DATE)`)
