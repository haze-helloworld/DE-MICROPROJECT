-- dim_repository.sql
-- One row per repository with enriched metadata and activity flag.

with repos as (
    select * from {{ ref('stg_repositories') }}
),

commits_summary as (
    select
        full_name,
        max(committed_at)   as last_commit_at,
        count(*)            as total_commits
    from {{ ref('stg_commits') }}
    group by 1
)

select
    r.repo_id,
    r.full_name,
    r.owner_login,
    r.repo_name,
    r.primary_language,
    r.description,
    r.stars,
    r.forks,
    r.open_issues,
    r.watchers,
    r.size_kb,
    r.visibility,
    r.created_at,
    r.pushed_at,
    c.last_commit_at,
    coalesce(c.total_commits, 0)    as total_commits,
    -- "Active" = pushed within last 365 days or high community adoption (>1000 stars)
    case
        when r.pushed_at >= dateadd('day', -365, current_date()) or r.stars > 1000 then true
        else false
    end                             as is_active
from repos r
left join commits_summary c using (full_name)

