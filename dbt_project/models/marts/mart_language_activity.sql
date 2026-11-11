-- mart_language_activity.sql
-- Answers the core dashboard question:
-- "Which programming languages have the most active repositories?"

with repos as (
    select * from {{ ref('dim_repository') }}
    where is_active
),

commits as (
    select * from {{ ref('int_commits_by_repo_month') }}
),

languages as (
    select * from {{ ref('stg_repo_languages') }}
)

select
    r.primary_language                          as language,
    count(distinct r.repo_id)                   as active_repo_count,
    sum(r.stars)                                as total_stars,
    sum(r.forks)                                as total_forks,
    sum(r.open_issues)                          as total_open_issues,
    sum(r.total_commits)                        as total_commits,
    round(avg(r.stars), 0)                      as avg_stars_per_repo,
    round(avg(r.total_commits), 0)              as avg_commits_per_repo
from repos r
where r.primary_language is not null
group by 1
order by active_repo_count desc

