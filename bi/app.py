"""
bi/app.py
Conversational BI Interface for GitHub Developer Ecosystem Analytics
Queries Snowflake Data Marts in real time and answers natural language questions with interactive charts.
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import snowflake.connector
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization

load_dotenv()

st.set_page_config(
    page_title="GitHub Analytics - Conversational BI",
    page_icon="📊",
    layout="wide"
)

# ── Snowflake Connection Helper ───────────────────────────────────────────────

@st.cache_resource
def get_snowflake_connection():
    key_path = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH", "rsa_key.p8")
    with open(key_path, "rb") as fh:
        key = serialization.load_pem_private_key(fh.read(), password=None)
    pk = key.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return snowflake.connector.connect(
        account=os.environ.get("SNOWFLAKE_ACCOUNT", "IWQNQNR-IJ38491"),
        user=os.environ.get("SNOWFLAKE_USER", "SVC_INGEST"),
        private_key=pk,
        role="INGEST_ROLE",
        warehouse="GH_WH",
        database="GITHUB_ANALYTICS",
        schema="RAW"
    )

def run_query(query: str) -> pd.DataFrame:
    conn = get_snowflake_connection()
    with conn.cursor() as cur:
        cur.execute(query)
        cols = [desc[0].lower() for desc in cur.description]
        data = cur.fetchall()
        return pd.DataFrame(data, columns=cols)

# ── UI Header ─────────────────────────────────────────────────────────────────

st.title("🤖 GitHub Developer Ecosystem - Conversational BI")
st.caption("Ask questions about programming languages, repo activity, issues, and developer contributions.")

# ── Sidebar Quick Metrics & Add Repo ──────────────────────────────────────────

REPOS_TXT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ingestion", "repos.txt")

def get_tracked_repos() -> list[str]:
    if os.path.exists(REPOS_TXT_PATH):
        with open(REPOS_TXT_PATH, "r") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return []

def add_repo_and_ingest(repo_full_name: str):
    from ingestion.extractor import extract_repo, load_to_snowflake
    import subprocess, sys
    
    # 1. Update repos.txt if not already present
    current_repos = get_tracked_repos()
    if repo_full_name not in current_repos:
        with open(REPOS_TXT_PATH, "a") as f:
            f.write(f"\n{repo_full_name}")
    
    # 2. Ingest the repo into Snowflake immediately
    conn = get_snowflake_connection()
    with conn.cursor() as cur:
        data = extract_repo(repo_full_name)
        for table, rows in data.items():
            load_to_snowflake(cur, table, rows)

    # 3. Rebuild dbt Data Marts so BI analytics refresh automatically
    dbt_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dbt_project")
    subprocess.run([sys.executable, "-m", "dbt.cli.main", "run", "--target", "prod"], cwd=dbt_dir, capture_output=True)

with st.sidebar:
    st.header("⚡ Pipeline Status")
    st.success("Target: Snowflake (GITHUB_ANALYTICS)")
    st.info("Orchestration: Apache Airflow")
    st.info("Ingestion: Airbyte / Extractor")
    st.info("Transform: dbt Core")
    
    st.markdown("---")
    st.subheader("➕ Add Public Repository")
    st.caption("Track any GitHub repo dynamically into Snowflake:")
    
    new_repo = st.text_input("Enter owner/repo (e.g. vuejs/vue):", key="new_repo_input")
    if st.button("🚀 Ingest Repo into Snowflake"):
        if new_repo and "/" in new_repo:
            with st.spinner(f"Extracting {new_repo} from GitHub and loading into Snowflake..."):
                try:
                    add_repo_and_ingest(new_repo.strip())
                    st.success(f"✅ Successfully ingested {new_repo} into Snowflake!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to ingest: {e}")
        else:
            st.warning("Please enter in format: owner/repo")

    # Display currently tracked repos
    tracked = get_tracked_repos()
    if tracked:
        with st.expander(f"📁 Tracked Repositories ({len(tracked)})"):
            for r in tracked:
                st.code(r, language="text")

    st.markdown("---")
    st.subheader("💡 Example Questions to Ask:")
    examples = [
        "Which programming languages have the most active repositories?",
        "Show commit activity across repos",
        "Which repositories have the most stars and forks?",
        "What is the issue resolution and close rate?",
        "Who are the top developer contributors?"
    ]
    for ex in examples:
        if st.button(ex):
            st.session_state.user_question = ex

# ── Conversational Query Logic ────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello Tanvi! I can answer questions about your GitHub data. Ask me anything or choose one from the sidebar!"}
    ]

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "chart" in msg:
            st.plotly_chart(msg["chart"], use_container_width=True)
        if "data" in msg:
            st.dataframe(msg["data"], use_container_width=True)

# User input
user_input = st.chat_input("Ask a question about your GitHub ecosystem...")
if "user_question" in st.session_state:
    user_input = st.session_state.pop("user_question")

if user_input:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # Process response
    q_lower = user_input.lower()
    
    with st.chat_message("assistant"):
        with st.spinner("Analyzing Snowflake data..."):
            try:
                # 1. Which languages have the most active repositories?
                if "language" in q_lower or "active repo" in q_lower:
                    sql = """
                    SELECT 
                        language,
                        total_bytes,
                        repo_count,
                        pct_of_ecosystem
                    FROM MARTS.MART_LANGUAGE_ACTIVITY
                    ORDER BY total_bytes DESC
                    """
                    df = run_query(sql)
                    fig = px.bar(
                        df, x="language", y="total_bytes", color="language",
                        title="Ecosystem Language Share (dbt Mart: MART_LANGUAGE_ACTIVITY)",
                        text_auto=True
                    )
                    reply = "Here is the language ecosystem breakdown materialized by dbt in `MARTS.MART_LANGUAGE_ACTIVITY`:"
                    st.write(reply)
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(df, use_container_width=True)
                    st.session_state.messages.append({"role": "assistant", "content": reply, "chart": fig, "data": df})

                # 2. Commits
                elif "commit" in q_lower or "velocity" in q_lower:
                    sql = """
                    SELECT 
                        full_name as repo_name,
                        total_commits,
                        stars,
                        forks
                    FROM MARTS.DIM_REPOSITORY
                    ORDER BY total_commits DESC
                    """
                    df = run_query(sql)
                    fig = px.bar(
                        df, x="repo_name", y="total_commits", color="repo_name",
                        title="Commit Velocity Across Repositories (dbt Mart: DIM_REPOSITORY)",
                        text_auto=True
                    )
                    reply = "Here is the commit volume across tracked repositories from `MARTS.DIM_REPOSITORY`:"
                    st.write(reply)
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(df, use_container_width=True)
                    st.session_state.messages.append({"role": "assistant", "content": reply, "chart": fig, "data": df})

                # 3. Stars / Forks / Health
                elif "star" in q_lower or "fork" in q_lower or "repo" in q_lower or "health" in q_lower:
                    sql = """
                    SELECT 
                        full_name as repo,
                        primary_language as language,
                        stars,
                        forks,
                        open_issues,
                        total_commits
                    FROM MARTS.DIM_REPOSITORY
                    ORDER BY stars DESC
                    """
                    df = run_query(sql)
                    fig = px.scatter(
                        df, x="stars", y="forks", size="stars", color="language", hover_name="repo",
                        title="Repository Community Health: Stars vs. Forks (dbt Mart: DIM_REPOSITORY)"
                    )
                    reply = "Here is the community health and engagement comparison materialized in `MARTS.DIM_REPOSITORY`:"
                    st.write(reply)
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(df, use_container_width=True)
                    st.session_state.messages.append({"role": "assistant", "content": reply, "chart": fig, "data": df})

                # 4. Issues & Resolution
                elif "issue" in q_lower or "resolution" in q_lower or "bug" in q_lower:
                    sql = """
                    SELECT 
                        full_name as repo,
                        total_issues,
                        closed_issues,
                        open_issues,
                        avg_resolution_hours,
                        median_resolution_hours
                    FROM MARTS.MART_ISSUE_RESOLUTION
                    ORDER BY total_issues DESC
                    """
                    df = run_query(sql)
                    df["close_rate_pct"] = (df["closed_issues"] / df["total_issues"] * 100).round(1)
                    fig = px.bar(
                        df, x="repo", y=["closed_issues", "open_issues"],
                        barmode="group", title="Issue State Distribution (dbt Mart: MART_ISSUE_RESOLUTION)"
                    )
                    reply = "Here is the issue resolution efficiency and lifecycle analysis from `MARTS.MART_ISSUE_RESOLUTION`:"
                    st.write(reply)
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(df, use_container_width=True)
                    st.session_state.messages.append({"role": "assistant", "content": reply, "chart": fig, "data": df})

                # 5. Top developers / contributors
                elif "developer" in q_lower or "contributor" in q_lower or "who" in q_lower or "author" in q_lower:
                    sql = """
                    SELECT 
                        author_login as contributor,
                        total_commits,
                        repos_contributed_to,
                        first_commit_at,
                        last_commit_at
                    FROM MARTS.MART_DEVELOPER_ACTIVITY
                    ORDER BY total_commits DESC
                    LIMIT 15
                    """
                    df = run_query(sql)
                    fig = px.bar(
                        df, x="contributor", y="total_commits", color="total_commits",
                        title="Top Developer Contributors (dbt Mart: MART_DEVELOPER_ACTIVITY)",
                        text_auto=True
                    )
                    reply = "Here are the top contributing developers materialized in `MARTS.MART_DEVELOPER_ACTIVITY`:"
                    st.write(reply)
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(df, use_container_width=True)
                    st.session_state.messages.append({"role": "assistant", "content": reply, "chart": fig, "data": df})

                else:
                    reply = f"I examined your query '{user_input}'. Try asking about 'languages', 'commits', 'stars', 'issues', or 'top developers'!"
                    st.write(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})

            except Exception as exc:
                err_msg = f"Failed to query Snowflake: {exc}"
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})
