-- stg_repo_languages.sql
-- Unpivots the language-bytes map into one row per repo+language.

with src as (
    select payload, loaded_at
    from {{ source('github_raw', 'repo_languages') }}
),

parsed as (
    select
        payload:repo::string  as full_name,
        payload:languages     as languages_map,
        loaded_at
    from src
),

-- Flatten the map {Python: 123456, SQL: 7890, ...} into rows
flattened as (
    select
        p.full_name,
        f.key::string   as language,
        f.value::number as bytes,
        p.loaded_at
    from parsed p,
    lateral flatten(input => p.languages_map) f
)

select * from flattened

