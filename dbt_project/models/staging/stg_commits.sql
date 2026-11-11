-- stg_commits.sql
-- Parses raw commit payloads. One row per commit SHA.

with src as (
    select payload, loaded_at
    from {{ source('github_raw', 'commits') }}
),

parsed as (
    select
        payload:sha::string                              as commit_sha,
        payload:repo::string                             as full_name,
        payload:commit:author:name::string               as author_name,
        payload:commit:author:email::string              as author_email,
        payload:commit:author:date::timestamp_tz         as committed_at,
        payload:commit:message::string                   as commit_message,
        payload:commit:comment_count::number             as comment_count,
        payload:author:login::string                     as author_login,
        loaded_at
    from src
)

select * from parsed
qualify row_number() over (partition by commit_sha order by loaded_at desc) = 1
