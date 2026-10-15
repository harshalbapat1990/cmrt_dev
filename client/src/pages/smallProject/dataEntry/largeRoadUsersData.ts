import type { ActivityDataCreate, ActivityDataOut } from "@/services/ActivityData.service";
import { activityToRoadUserRow } from "./roadUserMapping";
import { toNumberOrNull, type UserCalculationSummary } from "./roadUserCalculations";
import type { RoadParams, RoadUserRow, RoadUserYearData } from "./roadUserTypes";
import { getSpeed, isRoadRowComplete } from "./roadUserCalculations";

export function emptyRoadUserYear(
  vehicleTypes: string[],
  params: RoadParams,
  idPrefix = "road-new",
): RoadUserYearData {
  return {
    params: { ...params },
    rows: vehicleTypes.map((vehicleType, index) => ({
      id: `${idPrefix}-${index}`,
      vehicleType,
      vkt: "",
      vht: "",
      avgSpeed: "",
      lastEdited: null,
      notes: "",
    })),
  };
}

function extraFields(activity: ActivityDataOut): Record<string, unknown> {
  const value: unknown = activity.extra_fields;
  return typeof value === "object" && value !== null
    ? value as Record<string, unknown>
    : {};
}

function readRoadParams(activity: ActivityDataOut, defaults: RoadParams): RoadParams {
  const fields = extraFields(activity);
  const getStringOrDefault = (key: keyof RoadParams) =>
    typeof fields[key] === "string" ? fields[key] as string : defaults[key];

  return {
    ev_uptake_scenario: getStringOrDefault("ev_uptake_scenario"),
    roughness: getStringOrDefault("roughness"),
    gradient: getStringOrDefault("gradient"),
    curvature: getStringOrDefault("curvature"),
  };
}

export function buildLargeRoadUserYears(
  paramsRows: ActivityDataOut[],
  userRows: ActivityDataOut[],
  vehicleTypes: string[],
  requiredYears: number[],
  defaults: RoadParams,
): {
  globalParams: RoadParams;
  years: Record<number, RoadUserYearData>;
  summaryFields: Record<string, unknown> | null;
} {
  const firstParams = paramsRows.find((row) => row.extra_fields != null);
  const globalParams = firstParams ? readRoadParams(firstParams, defaults) : { ...defaults };
  const summaryFields = firstParams ? extraFields(firstParams) : null;
  const years: Record<number, RoadUserYearData> = {};

  for (const row of paramsRows) {
    const year = extraFields(row).modelled_year;
    if (typeof year === "number") {
      years[year] = emptyRoadUserYear(vehicleTypes, globalParams, `road-empty-${year}`);
    }
  }

  for (const row of userRows) {
    const fields = extraFields(row);
    const year = fields.modelled_year;
    const vehicleType = fields.vehicle_type;
    if (typeof year !== "number" || typeof vehicleType !== "string") continue;

    years[year] ??= emptyRoadUserYear(vehicleTypes, globalParams);
    const rowIndex = years[year].rows.findIndex((item) => item.vehicleType === vehicleType);
    if (rowIndex >= 0) {
      const mapped: RoadUserRow = activityToRoadUserRow(
        row,
        vehicleType,
        `road-empty-${year}-${rowIndex}`,
      );
      years[year].rows[rowIndex] = mapped;
    }
  }

  for (const year of requiredYears) {
    years[year] ??= emptyRoadUserYear(vehicleTypes, globalParams);
  }

  return { globalParams, years, summaryFields };
}

export interface LargeRoadCalculationInput {
  years: number[];
  yearData: Record<number, RoadUserYearData>;
  projectId: string;
  stageInstanceId: string;
  projectOptionId?: string | null;
}

type LargeRoadAnchorYear = {
  year: number;
  vehicles: Array<{
    vehicle_type: string;
    vkt: number;
    speed_kmh?: number;
    average_speed_kph?: number;
  }>;
};

export type LargeRoadCalculationPayload = Record<string, unknown> & {
  anchor_years: LargeRoadAnchorYear[];
};

function calculationAnchorYears(
  years: number[],
  yearData: Record<number, RoadUserYearData>,
  normalizeVehicleType: (vehicleType: string) => string,
  speedField: "speed_kmh" | "average_speed_kph",
): LargeRoadAnchorYear[] {
  return years
    .map((year) => ({
      year,
      vehicles: (yearData[year]?.rows ?? [])
        .filter(isRoadRowComplete)
        .map((row) => ({
          vehicle_type: normalizeVehicleType(row.vehicleType),
          vkt: Number(row.vkt),
          [speedField]: Number(getSpeed(row)),
        })),
    }))
    .filter((anchorYear) => anchorYear.vehicles.length > 0);
}

export function buildLargeNzRoadCalculationPayload({
  years,
  yearData,
  projectId,
  stageInstanceId,
  projectOptionId,
}: LargeRoadCalculationInput): LargeRoadCalculationPayload | null {
  const anchor_years = calculationAnchorYears(
    years,
    yearData,
    (vehicleType) => vehicleType.toLowerCase().replace(/\s+/g, "_"),
    "speed_kmh",
  );
  if (anchor_years.length === 0) return null;
  return {
    project_id: projectId,
    project_option_id: projectOptionId,
    project_stage_instance_id: stageInstanceId,
    anchor_years,
  };
}

export function buildLargeAusRoadCalculationPayload(
  input: LargeRoadCalculationInput & { params: RoadParams },
): LargeRoadCalculationPayload | null {
  const anchor_years = calculationAnchorYears(
    input.years,
    input.yearData,
    (vehicleType) => vehicleType,
    "average_speed_kph",
  );
  if (anchor_years.length === 0) return null;
  return {
    project_id: input.projectId,
    project_option_id: input.projectOptionId,
    project_stage_instance_id: input.stageInstanceId,
    roughness: input.params.roughness,
    gradient: input.params.gradient,
    curvature: input.params.curvature,
    ev_uptake_scenario: input.params.ev_uptake_scenario,
    anchor_years,
  };
}

export interface LargeRoadPersistenceInput {
  years: number[];
  yearData: Record<number, RoadUserYearData>;
  params: RoadParams;
  summary: UserCalculationSummary;
  projectId: string;
  stageInstanceId: string;
  projectOptionId: string | null | undefined;
  paramsTableKey: string;
  usersTableKey: string;
  projectMitigationId?: string | null;
}

export function buildLargeRoadUserPersistencePayloads({
  years,
  yearData,
  params,
  summary,
  projectId,
  stageInstanceId,
  projectOptionId,
  paramsTableKey,
  usersTableKey,
  projectMitigationId,
}: LargeRoadPersistenceInput): {
  paramsPayload: ActivityDataCreate[];
  usersPayload: ActivityDataCreate[];
} {
  const mitigationScope = projectMitigationId
    ? { project_mitigation_id: projectMitigationId }
    : {};
  const paramsPayload: ActivityDataCreate[] = years.map((year) => ({
    project_id: projectId,
    project_stage_instance_id: stageInstanceId,
    project_option_id: projectOptionId ?? null,
    metric_id: null,
    quantity: 0,
    unit_id: null,
    ui_table_key: paramsTableKey,
    extra_fields: {
      modelled_year: year,
      ev_uptake_scenario: params.ev_uptake_scenario,
      roughness: params.roughness,
      gradient: params.gradient,
      curvature: params.curvature,
      interim_total_tco2e: summary.absoluteEmissions ?? null,
      base_case_emissions_tco2e: summary.baseCaseAbsoluteEmissions ?? null,
      final_user_emissions_tco2e: summary.relativeUserEmissions ?? null,
    },
    ...mitigationScope,
  }));
  const usersPayload: ActivityDataCreate[] = years.flatMap((year) =>
    (yearData[year]?.rows ?? [])
      .filter((row) => toNumberOrNull(row.vkt) != null)
      .map((row) => ({
        project_id: projectId,
        project_stage_instance_id: stageInstanceId,
        project_option_id: projectOptionId ?? null,
        metric_id: null,
        quantity: toNumberOrNull(row.vkt) ?? 0,
        unit_id: null,
        ui_table_key: usersTableKey,
        extra_fields: {
          modelled_year: year,
          vehicle_type: row.vehicleType,
          vkt: row.vkt,
          vht: row.vht || null,
          avg_speed: row.avgSpeed || null,
          last_edited: row.lastEdited,
          notes: row.notes || null,
        },
        ...mitigationScope,
      })),
  );
  return { paramsPayload, usersPayload };
}
