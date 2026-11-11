"""
scripts/test_connections.py
Quick sanity-check: verifies GitHub API and Snowflake are reachable.
Run from the project root:  python scripts/test_connections.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PASS = "✅"
FAIL = "❌"


def test_github() -> bool:
    import requests

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print(f"{FAIL} GITHUB_TOKEN not set in .env")
        return False

    resp = requests.get(
        "https://api.github.com/rate_limit",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if resp.status_code == 200:
        core = resp.json()["resources"]["core"]
        print(
            f"{PASS} GitHub API — remaining: {core['remaining']}/{core['limit']} requests"
        )
        return True
    else:
        print(f"{FAIL} GitHub API — status {resp.status_code}: {resp.text[:200]}")
        return False


def test_snowflake() -> bool:
    import snowflake.connector
    from cryptography.hazmat.primitives import serialization

    key_path = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH", "")
    if not key_path or not Path(key_path).exists():
        print(f"{FAIL} SNOWFLAKE_PRIVATE_KEY_PATH not set or file not found")
        return False

    try:
        with open(key_path, "rb") as fh:
            key = serialization.load_pem_private_key(fh.read(), password=None)
        pk = key.private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )

        con = snowflake.connector.connect(
            account=os.environ["SNOWFLAKE_ACCOUNT"],
            user=os.environ["SNOWFLAKE_USER"],
            private_key=pk,
            role="INGEST_ROLE",
            warehouse="GH_WH",
            database="GITHUB_ANALYTICS",
            schema="RAW",
        )
        cur = con.cursor()
        cur.execute("SELECT CURRENT_VERSION(), CURRENT_ROLE(), CURRENT_WAREHOUSE()")
        version, role, warehouse = cur.fetchone()
        print(f"{PASS} Snowflake — version: {version}  role: {role}  warehouse: {warehouse}")
        cur.close()
        con.close()
        return True

    except Exception as exc:
        print(f"{FAIL} Snowflake — {exc}")
        return False


if __name__ == "__main__":
    print("\n── Connection tests ───────────────────────────────")
    gh_ok = test_github()
    sf_ok = test_snowflake()
    print("───────────────────────────────────────────────────\n")

    if gh_ok and sf_ok:
        print("All connections OK — ready to run the extractor 🚀")
        sys.exit(0)
    else:
        print("Fix the failing connection(s) above, then re-run.")
        sys.exit(1)

