-- int_issue_resolution.sql
-- Calculates per-repo issue resolution stats.

with issues as (
    select * from {{ ref('stg_issues') }}
)

select
    full_name,
    count(*)                                                    as total_issues,
    countif(state = 'closed')                                   as closed_issues,
    countif(state = 'open')                                     as open_issues,
    round(avg(resolution_hours), 1)                             as avg_resolution_hours,
    round(median(resolution_hours), 1)                          as median_resolution_hours,
    round(avg(case when state = 'closed'
                   then resolution_hours end), 1)               as avg_closed_resolution_hours
from issues
group by 1

