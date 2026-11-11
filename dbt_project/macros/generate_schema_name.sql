{% macro generate_schema_name(custom_schema_name, node) -%}
  {#
    In prod:  use the custom schema name as-is → STAGING, INTERMEDIATE, MARTS
    In dev:   prefix with target schema        → DEV_TANVI_staging, etc.
  #}
  {%- if target.name == 'prod' and custom_schema_name is not none -%}
    {{ custom_schema_name | trim | upper }}
  {%- else -%}
    {{ target.schema }}{{ '_' + custom_schema_name if custom_schema_name else '' }}
  {%- endif -%}
{%- endmacro %}

