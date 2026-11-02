-- =====================================================================
-- Create View: Grade 1 Asset Level Pivoted Data
-- =====================================================================
-- This view converts normalized band_code + lifecycle_module_code structure 
-- into Excel-style pivoted columns (Low/Mid/High for each stage)
-- Handles duplicate rows by keeping only the first (original) record

CREATE OR REPLACE VIEW v_grade1_asset_level_pivoted AS
SELECT 
    "Jurisdiction",
    "Mastertype",
    "Typecast",
    "Source",
    MAX("Functional_Unit") AS "Functional_Unit",
    -- Material Share columns
    MAX(CASE WHEN lifecycle_module_code IS NULL AND band_code = 'Low' THEN value END) 
        AS "Material share of capex - Low",
    MAX(CASE WHEN lifecycle_module_code IS NULL AND band_code = 'Mid' THEN value END) 
        AS "Material share of capex - Mid",
    MAX(CASE WHEN lifecycle_module_code IS NULL AND band_code = 'High' THEN value END) 
        AS "Material share of capex - High",
    -- Product stage (A1-A3) columns
    MAX(CASE WHEN lifecycle_module_code = 'A1-A3' AND band_code = 'Low' THEN value END) 
        AS "Product stage (A1-A3) - Low",
    MAX(CASE WHEN lifecycle_module_code = 'A1-A3' AND band_code = 'Mid' THEN value END) 
        AS "Product stage (A1-A3) - Mid",
    MAX(CASE WHEN lifecycle_module_code = 'A1-A3' AND band_code = 'High' THEN value END) 
        AS "Product stage (A1-A3) - High",
    -- Transport (A4) columns
    MAX(CASE WHEN lifecycle_module_code = 'A4' AND band_code = 'Low' THEN value END) 
        AS "transport (A4) - Low",
    MAX(CASE WHEN lifecycle_module_code = 'A4' AND band_code = 'Mid' THEN value END) 
        AS "transport (A4) - Mid",
    MAX(CASE WHEN lifecycle_module_code = 'A4' AND band_code = 'High' THEN value END) 
        AS "transport (A4) - High",
    -- Construction (A5) columns
    MAX(CASE WHEN lifecycle_module_code = 'A5' AND band_code = 'Low' THEN value END) 
        AS "Construction (A5) - Low",
    MAX(CASE WHEN lifecycle_module_code = 'A5' AND band_code = 'Mid' THEN value END) 
        AS "Construction (A5) - Mid",
    MAX(CASE WHEN lifecycle_module_code = 'A5' AND band_code = 'High' THEN value END) 
        AS "Construction (A5) - High"
FROM (
    -- Use DISTINCT ON to eliminate duplicates - keeps first row (by ID) for each combo
    SELECT DISTINCT ON (
        bgm.jurisdiction_id,
        bgm.typecast_name,
        bgm.source,
        bgm.lifecycle_module_code,
        bgm.band_code,
        bgm.metric_type_id
    )
        j.name AS "Jurisdiction",
        bgm.mastertype AS "Mastertype",
        bgm.typecast_name AS "Typecast",
        bgm.source AS "Source",
        u.code AS "Functional_Unit",
        bgm.lifecycle_module_code,
        bgm.band_code,
        bgm.value
    FROM background_grade_metrics bgm
    JOIN jurisdictions j ON bgm.jurisdiction_id = j.id
    LEFT JOIN units u ON bgm.unit_id = u.id
    WHERE bgm.is_active = true
        AND bgm.grade_id = 1  -- Grade 1 Asset Level
    ORDER BY 
        bgm.jurisdiction_id,
        bgm.typecast_name,
        bgm.source,
        bgm.lifecycle_module_code,
        bgm.band_code,
        bgm.metric_type_id,
        bgm.created_at DESC,  -- Keep the newest record for each source
        bgm.value DESC,  -- Then prefer non-zero values if timestamps are equal
        bgm.id ASC
) normalized
GROUP BY 
    "Jurisdiction",
    "Mastertype",
    "Typecast",
    "Source"
ORDER BY 
    "Jurisdiction",
    "Mastertype",
    "Typecast",
    "Source";

-- =====================================================================
-- Usage Examples:
-- =====================================================================

-- View all pivoted data:
-- SELECT * FROM v_grade1_asset_level_pivoted;

-- Filter by specific Jurisdiction:
-- SELECT * FROM v_grade1_asset_level_pivoted WHERE "Jurisdiction" = 'Australia';

-- Filter by specific Mastertype:
-- SELECT * FROM v_grade1_asset_level_pivoted WHERE "Mastertype" = 'Road';

-- Filter by specific Typecast:
-- SELECT * FROM v_grade1_asset_level_pivoted WHERE "Typecast" = 'Low Use Road';

-- =====================================================================
-- Drop view (if needed to recreate):
-- =====================================================================
-- DROP VIEW IF EXISTS v_grade1_asset_level_pivoted;
