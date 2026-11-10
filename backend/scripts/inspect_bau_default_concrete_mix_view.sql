-- Read-only pre-deployment inspection for public.v_bau_default_concrete_mix.
-- Run against each target database before applying the compatibility migration.

-- Existing output column contract and view definition.
SELECT
    a.attnum AS ordinal,
    a.attname AS column_name,
    pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type
FROM pg_attribute AS a
WHERE a.attrelid = to_regclass('public.v_bau_default_concrete_mix')
  AND a.attnum > 0
  AND NOT a.attisdropped
ORDER BY a.attnum;

SELECT pg_get_viewdef('public.v_bau_default_concrete_mix'::regclass, true) AS view_definition;

-- Owner and explicit grants.
SELECT
    c.relname AS view_name,
    pg_get_userbyid(c.relowner) AS owner,
    grant_info.grantee,
    grant_info.privilege_type,
    grant_info.is_grantable
FROM pg_class AS c
CROSS JOIN LATERAL aclexplode(coalesce(c.relacl, acldefault('r', c.relowner))) AS grant_info
WHERE c.oid = to_regclass('public.v_bau_default_concrete_mix')
ORDER BY grant_info.grantee, grant_info.privilege_type;

-- Views, materialized views, and rules that depend on this view.
SELECT DISTINCT
    dependent_ns.nspname AS dependent_schema,
    dependent.relname AS dependent_object,
    dependent.relkind AS dependent_kind
FROM pg_depend AS d
JOIN pg_rewrite AS rewrite ON rewrite.oid = d.objid
JOIN pg_class AS dependent ON dependent.oid = rewrite.ev_class
JOIN pg_namespace AS dependent_ns ON dependent_ns.oid = dependent.relnamespace
WHERE d.classid = 'pg_rewrite'::regclass
  AND d.refobjid = to_regclass('public.v_bau_default_concrete_mix')
  AND dependent.oid <> d.refobjid
ORDER BY dependent_ns.nspname, dependent.relname;

-- Alembic revision recorded by this database.
SELECT version_num FROM alembic_version;
