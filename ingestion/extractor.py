"""
GitHub → Snowflake extractor
Fetches repos, languages, commits, issues, and pull requests
for every owner/repo listed in ingestion/repos.txt, then loads
them as raw JSON (VARIANT) into Snowflake RAW schema.

Usage:
    python ingestion/extractor.py

Environment variables (set in .env):
    GITHUB_TOKEN                – GitHub fine-grained PAT
    SNOWFLAKE_ACCOUNT           – e.g. orgname-accountname
    SNOWFLAKE_USER              – SVC_INGEST
    SNOWFLAKE_PRIVATE_KEY_PATH  – absolute path to rsa_key.p8
"""

import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
BASE = "https://api.github.com"

# Only fetch commits/issues/PRs updated after this date (incremental window).
# For the first run this pulls ~90 days of history.
SINCE = datetime(2025, 8, 1, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

REPOS_FILE = Path(__file__).parent / "repos.txt"

# ── GitHub helpers ─────────────────────────────────────────────────────────────


def _handle_rate_limit(response: requests.Response) -> None:
    """Sleep until GitHub rate-limit resets if we hit a 403 / 429."""
    reset_ts = int(response.headers.get("X-RateLimit-Reset", time.time() + 60))
    wait = max(reset_ts - int(time.time()), 0) + 5
    log.warning("Rate-limited. Sleeping %ds …", wait)
    time.sleep(wait)


def get_all(url: str, params: dict | None = None):
    """
    Paginated GET — yields one item at a time.
    Follows the Link: <next> header automatically.
    """
    params = {**(params or {}), "per_page": 100}
    while url:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)

        if resp.status_code in (403, 429):
            remaining = resp.headers.get("X-RateLimit-Remaining", "1")
            if remaining == "0":
                _handle_rate_limit(resp)
                continue  # retry same URL

        resp.raise_for_status()

        data = resp.json()
        if isinstance(data, list):
            yield from data
        else:
            yield data

        url = resp.links.get("next", {}).get("url")
        params = None  # next URL already carries query params


# ── Snowflake helpers ──────────────────────────────────────────────────────────


def _load_private_key() -> bytes:
    key_path = os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]
    with open(key_path, "rb") as fh:
        key = serialization.load_pem_private_key(fh.read(), password=None)
    return key.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def get_connection() -> snowflake.connector.SnowflakeConnection:
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key=_load_private_key(),
        role="INGEST_ROLE",
        warehouse="GH_WH",
        database="GITHUB_ANALYTICS",
        schema="RAW",
    )


def load_to_snowflake(cur, table: str, rows: list[dict]) -> None:
    """
    Write rows as newline-delimited JSON to a temp file, PUT it into an
    internal stage, then COPY INTO the raw table (VARIANT column).
    Skips if rows is empty.
    """
    if not rows:
        log.info("  ↳ %s — no rows, skipping", table)
        return

    # Ensure the raw table and stage exist
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            payload    VARIANT,
            loaded_at  TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
        )
        """
    )
    cur.execute(f"CREATE STAGE IF NOT EXISTS stg_{table} FILE_FORMAT = (TYPE = JSON)")

    # Write rows to a temp NDJSON file and upload
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tmp:
        for row in rows:
            tmp.write(json.dumps(row) + "\n")
        tmp_path = tmp.name

    # On Windows, Snowflake PUT needs forward slashes
    put_path = tmp_path.replace("\\", "/")
    cur.execute(f"PUT file://{put_path} @stg_{table} OVERWRITE = TRUE AUTO_COMPRESS = TRUE")
    cur.execute(
        f"""
        COPY INTO {table} (payload)
        FROM (SELECT $1 FROM @stg_{table})
        FILE_FORMAT = (TYPE = JSON)
        PURGE = TRUE
        """
    )
    log.info("  ↳ %s — loaded %d rows", table, len(rows))


# ── Main extraction logic ──────────────────────────────────────────────────────


def extract_repo(full_name: str) -> dict[str, list]:
    """Fetch all entities for a single owner/repo. Returns a dict of table→rows."""
    owner, repo = full_name.split("/", 1)
    log.info("Extracting %s …", full_name)

    # Repository metadata (single object endpoint)
    meta = list(get_all(f"{BASE}/repos/{owner}/{repo}"))

    # Languages breakdown (single object — {language: bytes})
    lang_raw = next(get_all(f"{BASE}/repos/{owner}/{repo}/languages"), {})
    langs = [{"repo": full_name, "languages": lang_raw}]

    # Commits — incremental since SINCE
    commits = [
        {**c, "repo": full_name}
        for c in get_all(
            f"{BASE}/repos/{owner}/{repo}/commits",
            {"since": SINCE},
        )
    ]

    # Issues (includes PRs — we'll filter them apart in dbt)
    issues = [
        {**i, "repo": full_name}
        for i in get_all(
            f"{BASE}/repos/{owner}/{repo}/issues",
            {"state": "all", "since": SINCE},
        )
    ]

    # Pull requests
    prs = [
        {**p, "repo": full_name}
        for p in get_all(
            f"{BASE}/repos/{owner}/{repo}/pulls",
            {"state": "all"},
        )
    ]

    return {
        "REPOSITORIES": meta,
        "REPO_LANGUAGES": langs,
        "COMMITS": commits,
        "ISSUES": issues,
        "PULL_REQUESTS": prs,
    }


def main() -> None:
    repos = [
        line.strip()
        for line in REPOS_FILE.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if not repos:
        log.error("repos.txt is empty. Add at least one owner/repo.")
        sys.exit(1)

    log.info("Starting extraction for %d repos: %s", len(repos), repos)

    con = get_connection()
    cur = con.cursor()

    for full_name in repos:
        try:
            data = extract_repo(full_name)
            for table, rows in data.items():
                load_to_snowflake(cur, table, rows)
        except Exception as exc:  # noqa: BLE001
            log.error("Failed for %s: %s", full_name, exc, exc_info=True)
            # Continue with remaining repos rather than aborting the whole run

    cur.close()
    con.close()
    log.info("Extraction complete.")


if __name__ == "__main__":
    main()
