-- int_pr_lifecycle.sql
-- PR merge rates and cycle times per repository.

with prs as (
    select * from {{ ref('stg_pull_requests') }}
)

select
    full_name,
    count(*)                                        as total_prs,
    countif(is_merged)                              as merged_prs,
    countif(state = 'open')                         as open_prs,
    round(
        countif(is_merged) * 100.0 / nullifzero(count(*)), 1
    )                                               as merge_rate_pct,
    round(avg(merge_time_hours), 1)                 as avg_merge_time_hours,
    round(avg(additions + deletions), 0)            as avg_lines_changed
from prs
group by 1

