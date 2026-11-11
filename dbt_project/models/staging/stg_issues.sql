-- stg_issues.sql
-- Parses issues only (pull requests are excluded — they have a pull_request key).

with src as (
    select payload, loaded_at
    from {{ source('github_raw', 'issues') }}
),

parsed as (
    select
        payload:id::number                       as issue_id,
        payload:number::number                   as issue_number,
        payload:repo::string                     as full_name,
        payload:title::string                    as title,
        payload:state::string                    as state,
        payload:user:login::string               as author_login,
        payload:created_at::timestamp_tz         as created_at,
        payload:updated_at::timestamp_tz         as updated_at,
        payload:closed_at::timestamp_tz          as closed_at,
        payload:comments::number                 as comment_count,
        -- datediff in hours between open and close (null if still open)
        datediff(
            'hour',
            payload:created_at::timestamp_tz,
            payload:closed_at::timestamp_tz
        )                                        as resolution_hours,
        loaded_at
    from src
    -- Exclude pull requests (they have a non-null pull_request object)
    where payload:pull_request is null
)

select * from parsed
qualify row_number() over (partition by issue_id order by loaded_at desc) = 1

