-- mart_developer_activity.sql
-- Top contributors across all tracked repos.

with commits as (
    select * from {{ ref('stg_commits') }}
),

agg as (
    select
        author_login,
        count(distinct full_name)   as repos_contributed_to,
        count(*)                    as total_commits,
        min(committed_at)           as first_commit_at,
        max(committed_at)           as last_commit_at
    from commits
    where author_login is not null
    group by 1
)

select *
from agg
order by total_commits desc

