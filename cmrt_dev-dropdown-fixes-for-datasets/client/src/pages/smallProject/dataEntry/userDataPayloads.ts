import type { ActivityDataCreate } from "@/services/ActivityData.service";
import { getSpeed, isRoadRowComplete, toNumberOrNull } from "./roadUserCalculations";
import type { RailUserRow } from "./userDataMapping";
import type { RoadUserRow } from "./roadUserTypes";
import type { UserCalculationSummary } from "./roadUserCalculations";

export interface UserActivityContext {
  projectId: string;
  stageInstanceId: string;
  projectOptionId?: string | null;
  projectMitigationId?: string | null;
}

export type RoadCalculationPayload = Record<string, string | number | null | undefined>;

const ROAD_CALCULATION_KEYS: Record<string, { vkt: string; speed: string }> = {
  "light vehicle": { vkt: "light_vehicle_vkt", speed: "light_vehicle_speed_kmh" },
  "medium vehicle": { vkt: "medium_vehicle_vkt", speed: "medium_vehicle_speed_kmh" },
  "heavy vehicle": { vkt: "heavy_vehicle_vkt", speed: "heavy_vehicle_speed_kmh" },
  "super heavy vehicle": { vkt: "super_heavy_vehicle_vkt", speed: "super_heavy_vehicle_speed_kmh" },
  "general fleet": { vkt: "general_fleet_vkt", speed: "general_fleet_speed_kmh" },
  bus: { vkt: "bus_vkt", speed: "bus_speed_kmh" },
};

export function buildRoadCalculationPayload(
  rows: RoadUserRow[],
  context: UserActivityContext,
): RoadCalculationPayload | null {
  const completedRows = rows.filter(isRoadRowComplete);
  if (completedRows.length === 0) return null;

  const payload: RoadCalculationPayload = {
    project_id: context.projectId,
    project_option_id: context.projectOptionId,
    project_stage_instance_id: context.stageInstanceId,
  };

  for (const row of completedRows) {
    const keys = ROAD_CALCULATION_KEYS[row.vehicleType.trim().toLowerCase()];
    const vkt = toNumberOrNull(row.vkt);
    const speed = getSpeed(row);
    if (!keys || vkt == null || speed == null) continue;
    payload[keys.vkt] = vkt;
    payload[keys.speed] = speed;
  }

  return payload;
}

export function buildRoadActivityPayload(
  rows: RoadUserRow[],
  context: UserActivityContext,
  tableKey: string,
  summary: UserCalculationSummary,
): ActivityDataCreate[] {
  return rows
    .filter((row) => row.vkt !== "" && !Number.isNaN(Number.parseFloat(row.vkt)))
    .map((row) => ({
      project_id: context.projectId,
      project_stage_instance_id: context.stageInstanceId,
      project_option_id: context.projectOptionId ?? null,
      metric_id: null,
      quantity: Number.parseFloat(row.vkt),
      unit_id: null,
      ui_table_key: tableKey,
      extra_fields: {
        vehicle_type: row.vehicleType,
        vkt: row.vkt,
        vht: row.vht || null,
        avg_speed: row.avgSpeed || null,
        last_edited: row.lastEdited,
        notes: row.notes || null,
        absoluteEmissions: summary.absoluteEmissions ?? null,
        baseCaseAbsoluteEmissions: summary.baseCaseAbsoluteEmissions ?? null,
        relativeUserEmissions: summary.relativeUserEmissions ?? null,
        absolute_emissions: summary.absoluteEmissions ?? null,
        base_case_absolute_emissions: summary.baseCaseAbsoluteEmissions ?? null,
        relative_user_emissions: summary.relativeUserEmissions ?? null,
      },
      ...(context.projectMitigationId
        ? { project_mitigation_id: context.projectMitigationId }
        : {}),
    }));
}

export function buildRailActivityPayload(
  rows: RailUserRow[],
  context: UserActivityContext,
  tableKey: string,
  modelledYear?: number,
): ActivityDataCreate[] {
  return rows.map((row) => ({
    project_id: context.projectId,
    project_stage_instance_id: context.stageInstanceId,
    project_option_id: context.projectOptionId ?? null,
    metric_id: null,
    quantity: row.freight !== "" && !Number.isNaN(Number.parseFloat(row.freight))
      ? Number.parseFloat(row.freight)
      : 0,
    unit_id: null,
    ui_table_key: tableKey,
    extra_fields: {
      ...(modelledYear != null ? { modelled_year: modelledYear } : {}),
      vehicle_type: row.vehicleType,
      terrain: row.terrain,
      freight: row.freight || null,
      notes: row.notes || null,
      emissions_intensity_tco2e_kl: row.dieselEmissionsIntensity || null,
      emissions_annual_tco2e: row.dieselEmissions || null,
      emissions_total_ref_period_tco2e: row.dieselEmissionsTotalRefPeriod || null,
    },
    ...(context.projectMitigationId
      ? { project_mitigation_id: context.projectMitigationId }
      : {}),
  }));
}
