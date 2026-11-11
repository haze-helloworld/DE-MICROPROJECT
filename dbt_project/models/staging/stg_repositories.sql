-- stg_repositories.sql
-- Parses raw JSON payload from RAW.REPOSITORIES.
-- One row per repo (latest load wins via QUALIFY).

with src as (
    select payload, loaded_at
    from {{ source('github_raw', 'repositories') }}
),

parsed as (
    select
        payload:id::number                   as repo_id,
        payload:full_name::string            as full_name,
        payload:owner:login::string          as owner_login,
        payload:name::string                 as repo_name,
        payload:language::string             as primary_language,
        payload:description::string          as description,
        payload:stargazers_count::number     as stars,
        payload:forks_count::number          as forks,
        payload:open_issues_count::number    as open_issues,
        payload:watchers_count::number       as watchers,
        payload:size::number                 as size_kb,
        payload:default_branch::string       as default_branch,
        payload:topics::array                as topics,
        payload:visibility::string           as visibility,
        payload:created_at::timestamp_tz     as created_at,
        payload:updated_at::timestamp_tz     as updated_at,
        payload:pushed_at::timestamp_tz      as pushed_at,
        loaded_at
    from src
)

-- Keep only the most recent load per repo
select * from parsed
qualify row_number() over (partition by repo_id order by loaded_at desc) = 1

