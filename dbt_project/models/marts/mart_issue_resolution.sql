-- mart_issue_resolution.sql
-- Dashboard card: how fast do repos resolve issues?

select
    r.full_name,
    r.primary_language,
    r.stars,
    i.total_issues,
    i.open_issues,
    i.closed_issues,
    i.avg_resolution_hours,
    i.median_resolution_hours,
    round(i.closed_issues * 100.0 / nullifzero(i.total_issues), 1) as close_rate_pct
from {{ ref('int_issue_resolution') }} i
join {{ ref('dim_repository') }} r using (full_name)
order by r.stars desc

