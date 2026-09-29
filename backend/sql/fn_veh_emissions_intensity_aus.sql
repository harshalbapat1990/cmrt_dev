-- DROP FUNCTION public.fn_veh_emissions_intensity_aus(int4, text, text, numeric, numeric, numeric, numeric);

CREATE OR REPLACE FUNCTION public.fn_veh_emissions_intensity_aus(p_year integer, p_state text, p_scenario text, p_gradient numeric, p_curvature numeric, p_iri numeric, p_speed_kph numeric, p_dataset_revision_id uuid)
 RETURNS TABLE(vehicle_class text, ev_projection_category text, model_used text, coeff_a numeric, coeff_b numeric, base_fuel_l_per_100km numeric, k1 numeric, k2 numeric, k3 numeric, k4 numeric, k5 numeric, gvm_tonnes numeric, ice_fuel_consumption_l_per_100km numeric, primary_ice_fuel text, bev_pct numeric, fcev_pct numeric, hybrid_pct numeric, ice_pct numeric, phev_pct numeric, fleet_avg_fuel_consumption_l_per_100km numeric, fuel_emissions_intensity_tco2e_per_kl numeric, fleet_avg_elec_consumption_kwh_per_100km numeric, electricity_emissions_intensity_tco2e_per_mwh numeric, fleet_avg_emissions_intensity_gco2e_per_vkt numeric)
 LANGUAGE sql
 STABLE
AS $function$

WITH

-- ─────────────────────────────────────────────────────────────────────────────
-- CTE 1: base_params
-- Joins all per-vehicle-class lookup tables in one place.
-- Computes ICE fuel consumption (Excel col O) using the correct model branch:
--
--   Stop-start model (speed <= 60 km/h) — Excel col E = "Stop-start":
--     FC = A + B / speed
--     Source: Users - Stop-start sheet, cols B/C/D
--
--   Uninterrupted model (speed > 60 km/h) — Excel col E = "Uninterrupted":
--     FC = BaseFuel × (K1 + K2/speed + K3×speed² + K4×IRI + K5×GVM)
--     Source: Users - Uninterrupted sheet, matched on vehicle class + gradient + curvature
--     IRI = p_iri (user input), GVM from vehicle_masses table
-- ─────────────────────────────────────────────────────────────────────────────
base_params AS (
    SELECT
        vc.id                                       AS vehicle_class_id,
        vc.name                                     AS vehicle_class,
        vecr.ev_projection_category,
        vecr.primary_ice_fuel,
        vecr.hybrid_fuel_savings_pct,
        vecr.phev_fuel_savings_pct,
        vecr.bev_energy_shift_kwh_per_l,
        vecr.fcev_hydrogen_consumption_kwh_per_l,
        iv.coefficient_a,
        iv.coefficient_b,
        uv.base_fuel_l_per_100km,
        uv.k1,
        uv.k2,
        uv.k3,
        uv.k4,
        uv.k5,
        vm.gvm_tonnes,
        -- Excel col E
        CASE WHEN p_speed_kph <= 60.0 THEN 'Stop-start' ELSE 'Uninterrupted' END
            AS model_used,
        -- Excel col O
        CASE
            WHEN p_speed_kph <= 60.0 THEN
                -- Stop-start: FC = A + B / speed
                iv.coefficient_a
                + iv.coefficient_b / NULLIF(p_speed_kph, 0)
            ELSE
                -- Uninterrupted: FC = BaseFuel × (K1 + K2/speed + K3×speed² + K4×IRI + K5×GVM)
                uv.base_fuel_l_per_100km * (
                      uv.k1
                    + uv.k2 / NULLIF(p_speed_kph, 0)
                    + uv.k3 * p_speed_kph * p_speed_kph
                    + uv.k4 * p_iri
                    + uv.k5 * vm.gvm_tonnes
                )
        END AS ice_fuel_consumption_l_per_100km
    FROM vehicle_classes vc
    -- Vehicle energy conversion rates (Table57 in Excel)
    -- Provides: ev_projection_category, primary_ice_fuel, hybrid/PHEV savings%, BEV/FCEV energy factors
    JOIN LATERAL (
        SELECT rates.*
        FROM vehicle_energy_conversion_rates rates
        WHERE rates.vehicle_class_id = vc.id
          AND (rates.dataset_revision_id = p_dataset_revision_id OR rates.dataset_revision_id IS NULL)
        ORDER BY (rates.dataset_revision_id = p_dataset_revision_id) DESC NULLS LAST
        LIMIT 1
    ) vecr ON TRUE
    -- Uninterrupted coefficients — matched on gradient + curvature (user inputs)
    JOIN LATERAL (
        SELECT coefficients.*
        FROM uninterrupted_vehicles coefficients
        WHERE coefficients.vehicle_class_id = vc.id
          AND coefficients.gradient_m_per_km = p_gradient
          AND coefficients.curvature_deg_per_km = p_curvature
          AND (coefficients.dataset_revision_id = p_dataset_revision_id OR coefficients.dataset_revision_id IS NULL)
        ORDER BY (coefficients.dataset_revision_id = p_dataset_revision_id) DESC NULLS LAST
        LIMIT 1
    ) uv ON TRUE
    -- Stop-start coefficients
    JOIN LATERAL (
        SELECT coefficients.*
        FROM interrupted_vehicles coefficients
        WHERE coefficients.vehicle_class_id = vc.id
          AND (coefficients.dataset_revision_id = p_dataset_revision_id OR coefficients.dataset_revision_id IS NULL)
        ORDER BY (coefficients.dataset_revision_id = p_dataset_revision_id) DESC NULLS LAST
        LIMIT 1
    ) iv ON TRUE
    -- GVM for uninterrupted formula
    JOIN vehicle_masses vm
        ON vm.vehicle_class_id = vc.id
        AND vm.dataset_revision_id = p_dataset_revision_id
),

-- ─────────────────────────────────────────────────────────────────────────────
-- CTE 2: ev_uptake
-- Excel cols Q–U: BEV%, FCEV%, Hybrid%, ICE%, PHEV% for the given
-- state + scenario + vehicle category + year.
--
-- Excel formula (col Q, BEV example):
--   =SUMPRODUCT((tbl_EV_proj[Region]=C13) * (tbl_EV_proj[Scenario]=C14)
--               * (tbl_EV_proj[Vehicle Category]=C2)
--               * (tbl_EV_proj[Energy Type]="BEV"), tbl_EV_proj[year_col])
--
-- In DB: ev_uptake_factors filtered by jurisdiction + scenario + vehicle category
--        + energy type + year, then pivoted per vehicle class.
-- ─────────────────────────────────────────────────────────────────────────────
ev_uptake AS (
    SELECT
        bp.vehicle_class_id,
        MAX(CASE WHEN eet.name = 'BEV'    THEN euf.uptake_pct END) AS bev_pct,
        MAX(CASE WHEN eet.name = 'FCEV'   THEN euf.uptake_pct END) AS fcev_pct,
        MAX(CASE WHEN eet.name = 'Hybrid' THEN euf.uptake_pct END) AS hybrid_pct,
        MAX(CASE WHEN eet.name = 'ICE'    THEN euf.uptake_pct END) AS ice_pct,
        MAX(CASE WHEN eet.name = 'PHEV'   THEN euf.uptake_pct END) AS phev_pct
    FROM ev_uptake_factors euf
    JOIN ev_scenario_types est  ON euf.scenario_code        = est.code
    JOIN jurisdictions j        ON euf.jurisdiction_id      = j.id
    JOIN ev_vehicle_categories evc ON euf.vehicle_category_code = evc.code
    JOIN ev_energy_types eet    ON euf.energy_type_code     = eet.code
    -- Use the revision-selected vehicle/category mapping from base_params.
    JOIN base_params bp ON bp.ev_projection_category = evc.name
    WHERE euf.dataset_revision_id = p_dataset_revision_id
      AND est.name   = p_scenario
      AND j.name     = p_state
      AND euf.year   = p_year
    GROUP BY bp.vehicle_class_id
),

-- ─────────────────────────────────────────────────────────────────────────────
-- CTE 3: fuel_emission_factors
-- Excel col W: Fuel emissions intensity (tCO2e/kL) = scope1 + scope3
--
-- Excel formula:
--   =INDEX(tbl_detailed_level[Scope 1 EF (tCO2e/UoM)], MATCH(P20, tbl_detailed_level[Emissions Source], 0))
--   +INDEX(tbl_detailed_level[Scope 3 EF (tCO2e/UoM)], MATCH(P20, tbl_detailed_level[Emissions Source], 0))
--
-- In DB: v_grade34_detailed_level filtered by "Emissions Source" = primary_ice_fuel
-- ─────────────────────────────────────────────────────────────────────────────
fuel_emission_factors AS (
    SELECT DISTINCT ON ("Emissions Source")
        "Emissions Source"        AS emissions_source,
        "emission_factor_scope1"  AS ef_scope1,
        "emission_factor_scope3"  AS ef_scope3
    FROM v_grade34_detailed_level AS factor_row
    WHERE (to_jsonb(factor_row)->>'dataset_revision_id')::uuid = p_dataset_revision_id
      AND factor_row."Jurisdiction" IN (p_state, 'Australia', 'Global')
      AND factor_row."UoM" = 'kL'
      AND ("emission_factor_scope1" IS NOT NULL
           OR "emission_factor_scope3" IS NOT NULL)
    ORDER BY "Emissions Source",
             CASE
                 WHEN factor_row."Jurisdiction" = p_state THEN 0
                 WHEN factor_row."Jurisdiction" = 'Australia' THEN 1
                 ELSE 2
             END,
             "emission_factor_scope3" DESC NULLS LAST,
             "emission_factor_scope1" DESC NULLS LAST
),

-- ─────────────────────────────────────────────────────────────────────────────
-- CTE 4: electricity_emission_factor
-- Excel col Y: Electricity emissions intensity (tCO2e/MWh)
--             = scope2_location + scope3_location for the given state + year
--
-- Excel formula:
--   =INDEX(tbl_scope2_LB[year_col], MATCH(C13, tbl_scope2_LB[Region], 0), MATCH(year, year_headers, 0))
--   +INDEX(tbl_scope3_LB[year_col], MATCH(C13, tbl_scope3_LB[Region], 0), MATCH(year, year_headers, 0))
--
-- In DB: electric_decarb_factors filtered by grid region name + year,
--        factor_type_code IN ('scope2_location', 'scope3_location')
-- NOTE: grid_regions.name must match the p_state value (e.g. 'New South Wales')
-- ─────────────────────────────────────────────────────────────────────────────
electricity_emission_factor AS (
    SELECT
        CASE
            WHEN COUNT(*) FILTER (WHERE edf.factor_type_code = 'scope2_location' AND edf.value IS NOT NULL) > 0
             AND COUNT(*) FILTER (WHERE edf.factor_type_code = 'scope3_location' AND edf.value IS NOT NULL) > 0
            THEN MAX(CASE WHEN edf.factor_type_code = 'scope2_location' THEN edf.value END)
               + MAX(CASE WHEN edf.factor_type_code = 'scope3_location' THEN edf.value END)
            ELSE NULL
        END AS elec_ef_tco2e_per_mwh
    FROM electric_decarb_factors edf
    JOIN grid_regions gr ON edf.region_id = gr.id
    WHERE edf.dataset_revision_id = p_dataset_revision_id
      AND gr.name    = p_state
      AND edf.year   = p_year
      AND edf.factor_type_code IN ('scope2_location', 'scope3_location')
)

-- ─────────────────────────────────────────────────────────────────────────────
-- FINAL SELECT: assemble all intermediate values and compute final result
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    b.vehicle_class,
    b.ev_projection_category,
    b.model_used,
    b.coefficient_a                             AS coeff_a,
    b.coefficient_b                             AS coeff_b,
    b.base_fuel_l_per_100km,
    b.k1, b.k2, b.k3, b.k4, b.k5,
    b.gvm_tonnes,

    -- Excel col O: ICE fuel consumption
    b.ice_fuel_consumption_l_per_100km,
    b.primary_ice_fuel,

    -- Excel cols Q–U: EV fleet mix
    COALESCE(ev.bev_pct,    0)                  AS bev_pct,
    COALESCE(ev.fcev_pct,   0)                  AS fcev_pct,
    COALESCE(ev.hybrid_pct, 0)                  AS hybrid_pct,
    COALESCE(ev.ice_pct,    0)                  AS ice_pct,
    COALESCE(ev.phev_pct,   0)                  AS phev_pct,

    -- Excel col V: Fleet average fuel consumption (L/100km)
    -- = FC × ICE%                         (pure ICE vehicles)
    -- + FC × Hybrid% × hybrid_savings%    (hybrids use a fraction of ICE fuel)
    -- + FC × PHEV%   × phev_savings%      (PHEVs use a fraction of ICE fuel)
    -- BEV and FCEV contribute zero liquid fuel
    b.ice_fuel_consumption_l_per_100km * COALESCE(ev.ice_pct,    0)
    + b.ice_fuel_consumption_l_per_100km * COALESCE(ev.hybrid_pct, 0) * b.hybrid_fuel_savings_pct
    + b.ice_fuel_consumption_l_per_100km * COALESCE(ev.phev_pct,   0) * b.phev_fuel_savings_pct
        AS fleet_avg_fuel_consumption_l_per_100km,

    -- Excel col W: Fuel emissions intensity (tCO2e/kL) = scope1 + scope3
    COALESCE(fef.ef_scope1, 0) + COALESCE(fef.ef_scope3, 0)
        AS fuel_emissions_intensity_tco2e_per_kl,

    -- Excel col X: Fleet average electricity consumption (kWh/100km)
    -- = FC × BEV%  × bev_energy_shift (kWh/L)    (BEV: fuel consumption converted to kWh)
    -- + FC × FCEV% × fcev_h2_consumption (kWh/L)  (FCEV: hydrogen energy equivalent)
    b.ice_fuel_consumption_l_per_100km * COALESCE(ev.bev_pct,  0) * b.bev_energy_shift_kwh_per_l
    + b.ice_fuel_consumption_l_per_100km * COALESCE(ev.fcev_pct, 0) * b.fcev_hydrogen_consumption_kwh_per_l
        AS fleet_avg_elec_consumption_kwh_per_100km,

    -- Excel col Y: Electricity emissions intensity (tCO2e/MWh)
    ee.elec_ef_tco2e_per_mwh
        AS electricity_emissions_intensity_tco2e_per_mwh,

    -- Excel col Z: Fleet average emissions intensity (gCO2e/VKT)
    -- Formula: (((V×W + X×Y) / 1000) / 100) × 10^6
    --
    -- Unit derivation:
    --   V (L/100km) × W (tCO2e/kL)   = tCO2e/100000km  [L/100km × tCO2e/1000L]
    --   X (kWh/100km) × Y (tCO2e/MWh) = tCO2e/100000km  [kWh/100km × tCO2e/1000kWh]
    --   Sum is in tCO2e/100000km
    --   ÷1000 ÷100 × 10^6 converts to gCO2e/VKT
    CASE
      WHEN ev.vehicle_class_id IS NULL
        OR fef.emissions_source IS NULL
        OR ee.elec_ef_tco2e_per_mwh IS NULL
      THEN NULL
      ELSE (((
        -- fuel component
        (   b.ice_fuel_consumption_l_per_100km * COALESCE(ev.ice_pct,    0)
          + b.ice_fuel_consumption_l_per_100km * COALESCE(ev.hybrid_pct, 0) * b.hybrid_fuel_savings_pct
          + b.ice_fuel_consumption_l_per_100km * COALESCE(ev.phev_pct,   0) * b.phev_fuel_savings_pct
        ) * (COALESCE(fef.ef_scope1, 0) + COALESCE(fef.ef_scope3, 0))
        +
        -- electricity + hydrogen component
        (   b.ice_fuel_consumption_l_per_100km * COALESCE(ev.bev_pct,  0) * b.bev_energy_shift_kwh_per_l
          + b.ice_fuel_consumption_l_per_100km * COALESCE(ev.fcev_pct, 0) * b.fcev_hydrogen_consumption_kwh_per_l
        ) * ee.elec_ef_tco2e_per_mwh
    ) / 1000.0) / 100.0) * 1000000.0
    END
        AS fleet_avg_emissions_intensity_gco2e_per_vkt

FROM base_params b
LEFT JOIN ev_uptake ev
    ON ev.vehicle_class_id = b.vehicle_class_id
LEFT JOIN fuel_emission_factors fef
    ON fef.emissions_source = b.primary_ice_fuel
CROSS JOIN electricity_emission_factor ee

ORDER BY b.vehicle_class;

$function$
;


