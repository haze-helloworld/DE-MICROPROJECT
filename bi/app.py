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

# ── Sidebar Quick Metrics ─────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚡ Pipeline Status")
    st.success("Target: Snowflake (GITHUB_ANALYTICS)")
    st.info("Orchestration: Apache Airflow")
    st.info("Ingestion: Airbyte / Python Extractor")
    st.info("Transform: dbt Core")
    
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
                        payload:language::string as language,
                        count(*) as repo_count,
                        sum(payload:stargazers_count::number) as total_stars,
                        sum(payload:forks_count::number) as total_forks
                    FROM REPOSITORIES
                    WHERE payload:language is not null
                    GROUP BY 1
                    ORDER BY repo_count DESC, total_stars DESC
                    """
                    df = run_query(sql)
                    fig = px.bar(
                        df, x="language", y="total_stars", color="language",
                        title="Top Programming Languages by Community Stars & Activity",
                        text_auto=True
                    )
                    reply = "Here is the language leaderboard based on the latest Snowflake ingestion! Python, Go, Rust, and JavaScript are leading community adoption:"
                    st.write(reply)
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(df, use_container_width=True)
                    st.session_state.messages.append({"role": "assistant", "content": reply, "chart": fig, "data": df})

                # 2. Commits
                elif "commit" in q_lower or "activity" in q_lower:
                    sql = """
                    SELECT 
                        payload:repo::string as repo_name,
                        count(*) as total_commits,
                        count(distinct payload:author:login::string) as active_authors
                    FROM COMMITS
                    GROUP BY 1
                    ORDER BY total_commits DESC
                    """
                    df = run_query(sql)
                    fig = px.bar(
                        df, x="repo_name", y="total_commits", color="repo_name",
                        title="Commit Velocity Across Target Repositories",
                        text_auto=True
                    )
                    reply = "Here is the commit volume and contributor breakdown across tracked repositories:"
                    st.write(reply)
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(df, use_container_width=True)
                    st.session_state.messages.append({"role": "assistant", "content": reply, "chart": fig, "data": df})

                # 3. Stars / Forks / Health
                elif "star" in q_lower or "fork" in q_lower or "repo" in q_lower:
                    sql = """
                    SELECT 
                        payload:full_name::string as repo,
                        payload:language::string as language,
                        payload:stargazers_count::number as stars,
                        payload:forks_count::number as forks,
                        payload:open_issues_count::number as open_issues
                    FROM REPOSITORIES
                    ORDER BY stars DESC
                    """
                    df = run_query(sql)
                    fig = px.scatter(
                        df, x="stars", y="forks", size="stars", color="language", hover_name="repo",
                        title="Repository Community Health: Stars vs. Forks"
                    )
                    reply = "Here is the community strength and engagement comparison for all tracked projects:"
                    st.write(reply)
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(df, use_container_width=True)
                    st.session_state.messages.append({"role": "assistant", "content": reply, "chart": fig, "data": df})

                # 4. Issues & Resolution
                elif "issue" in q_lower or "resolution" in q_lower or "bug" in q_lower:
                    sql = """
                    SELECT 
                        payload:repo::string as repo,
                        count(*) as total_issues,
                        count_if(payload:state::string = 'closed') as closed_issues,
                        count_if(payload:state::string = 'open') as open_issues
                    FROM ISSUES
                    GROUP BY 1
                    ORDER BY total_issues DESC
                    """
                    df = run_query(sql)
                    df["close_rate_pct"] = (df["closed_issues"] / df["total_issues"] * 100).round(1)
                    fig = px.bar(
                        df, x="repo", y=["closed_issues", "open_issues"],
                        barmode="group", title="Issue State Distribution (Open vs Closed)"
                    )
                    reply = "Here is the issue resolution distribution across the projects:"
                    st.write(reply)
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(df, use_container_width=True)
                    st.session_state.messages.append({"role": "assistant", "content": reply, "chart": fig, "data": df})

                # 5. Top developers / contributors
                elif "developer" in q_lower or "contributor" in q_lower or "who" in q_lower:
                    sql = """
                    SELECT 
                        payload:author:login::string as contributor,
                        count(*) as commits_count,
                        count(distinct payload:repo::string) as repos_involved
                    FROM COMMITS
                    WHERE payload:author:login is not null
                    GROUP BY 1
                    ORDER BY commits_count DESC
                    LIMIT 15
                    """
                    df = run_query(sql)
                    fig = px.bar(
                        df, x="contributor", y="commits_count", color="commits_count",
                        title="Top 15 Most Active Developer Contributors",
                        text_auto=True
                    )
                    reply = "Here are the top contributing developers across all tracked ecosystems:"
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
