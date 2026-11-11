-- int_commits_by_repo_month.sql
-- Aggregates commit counts per repository per calendar month.
-- Used by: mart_language_activity, mart_developer_activity

with commits as (
    select * from {{ ref('stg_commits') }}
),

aggregated as (
    select
        full_name,
        date_trunc('month', committed_at)   as activity_month,
        count(*)                            as commit_count,
        count(distinct author_login)        as distinct_authors
    from commits
    group by 1, 2
)

select * from aggregated

