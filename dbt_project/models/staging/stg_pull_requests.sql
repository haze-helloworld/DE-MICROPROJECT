-- stg_pull_requests.sql
-- Parses pull request payloads.

with src as (
    select payload, loaded_at
    from {{ source('github_raw', 'pull_requests') }}
),

parsed as (
    select
        payload:id::number                       as pr_id,
        payload:number::number                   as pr_number,
        payload:repo::string                     as full_name,
        payload:title::string                    as title,
        payload:state::string                    as state,
        payload:user:login::string               as author_login,
        payload:merged::boolean                  as is_merged,
        payload:draft::boolean                   as is_draft,
        payload:created_at::timestamp_tz         as created_at,
        payload:updated_at::timestamp_tz         as updated_at,
        payload:closed_at::timestamp_tz          as closed_at,
        payload:merged_at::timestamp_tz          as merged_at,
        payload:additions::number                as additions,
        payload:deletions::number                as deletions,
        payload:changed_files::number            as changed_files,
        datediff(
            'hour',
            payload:created_at::timestamp_tz,
            payload:merged_at::timestamp_tz
        )                                        as merge_time_hours,
        loaded_at
    from src
)

select * from parsed
qualify row_number() over (partition by pr_id order by loaded_at desc) = 1

