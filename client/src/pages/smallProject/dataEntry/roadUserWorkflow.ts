import ActivityDataService, { type ActivityDataCreate, type ActivityDataOut } from "@/services/ActivityData.service";
import EmissionCalculationsService from "@/services/EmissionCalculations.service";
import { normalizeCalculationSummary, type UserCalculationSummary } from "./roadUserCalculations";
import type { RailUserRow } from "./userDataMapping";

export type RoadCalculationSize = "small" | "large";
export type RoadCalculationRegion = "AU" | "NZ";

export async function calculateRoadUserSummary(
  payload: Record<string, unknown>,
  region: RoadCalculationRegion,
  size: RoadCalculationSize,
): Promise<UserCalculationSummary> {
  const result = size === "large"
    ? region === "NZ"
      ? await EmissionCalculationsService.calculateLargeNzRoads(payload)
      : await EmissionCalculationsService.calculateLargeAusRoads(payload)
    : region === "NZ"
      ? await EmissionCalculationsService.calculateNzRoads(payload)
      : await EmissionCalculationsService.calculateAusRoads(payload);
  return normalizeCalculationSummary(result);
}

export async function calculateRailUserRow(
  projectId: string,
  row: RailUserRow,
): Promise<RailUserRow> {
  const response = await EmissionCalculationsService.calculateRail({
    project_id: projectId,
    rail_type: row.vehicleType,
    terrain: row.terrain,
    freight_quantity_gtk_per_year: Number(row.freight),
  });
  const result = typeof response === "object" && response !== null
    ? response as Record<string, unknown>
    : {};
  return {
    ...row,
    dieselEmissionsTotalRefPeriod: result.emissions_total_ref_period_tco2e != null
      ? String(result.emissions_total_ref_period_tco2e)
      : "",
  };
}

export async function persistUserActivityRows(
  stageInstanceId: string,
  tableKey: string,
  payload: ActivityDataCreate[],
  projectMitigationId?: string | null,
): Promise<ActivityDataOut[]> {
  return ActivityDataService.bulkUpsert(
    stageInstanceId,
    tableKey,
    payload,
    projectMitigationId ?? undefined,
  );
}
