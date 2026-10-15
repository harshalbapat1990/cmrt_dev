import type { ActivityDataOut } from "@/services/ActivityData.service";
import { activityToRoadUserRow } from "./roadUserMapping";
import type { RoadUserRow } from "./roadUserTypes";

export interface RailUserRow {
  id: string;
  vehicleType: string;
  terrain: string;
  freight: string;
  dieselEmissionsIntensity: string;
  dieselEmissions: string;
  dieselEmissionsTotalRefPeriod: string;
  notes: string;
}

export function emptyRoadUserRows(vehicleTypes: string[]): RoadUserRow[] {
  return vehicleTypes.map((vehicleType, index) => emptyRoadUserRow(vehicleType, index));
}

function emptyRoadUserRow(vehicleType: string, index: number): RoadUserRow {
  return {
    id: `road-${index + 1}`,
    vehicleType,
    vkt: "",
    vht: "",
    avgSpeed: "",
    lastEdited: null,
    notes: "",
  };
}

export function mapRoadUserRows(
  activities: ActivityDataOut[],
  vehicleTypes: string[],
): RoadUserRow[] {
  return vehicleTypes.map((vehicleType, index) => {
    const activity = activities.find((row) => row.extra_fields?.vehicle_type === vehicleType);
    return activity
      ? activityToRoadUserRow(activity, vehicleType, `road-${index + 1}`)
      : emptyRoadUserRow(vehicleType, index);
  });
}

function stringValue(value: unknown): string {
  return value == null ? "" : String(value);
}

function firstDefined(fields: Record<string, unknown>, ...keys: string[]): unknown {
  for (const key of keys) {
    if (fields[key] != null) return fields[key];
  }
  return undefined;
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null
    ? value as Record<string, unknown>
    : {};
}

export function mapRailUserRow(
  activity: ActivityDataOut,
  defaultRow: RailUserRow,
): RailUserRow {
  const fields = asRecord(activity.extra_fields);
  return {
    id: activity.id,
    vehicleType: defaultRow.vehicleType,
    terrain: stringValue(fields.terrain ?? defaultRow.terrain),
    freight: stringValue(fields.freight),
    dieselEmissionsIntensity: stringValue(firstDefined(fields,
      "dieselEmissionsIntensity",
      "diesel_emissions_intensity",
      "emissions_intensity_tco2e_kl",
    )),
    dieselEmissions: stringValue(firstDefined(fields,
      "dieselEmissions",
      "diesel_emissions",
      "emissions_annual_tco2e",
    )),
    dieselEmissionsTotalRefPeriod: stringValue(firstDefined(fields,
      "dieselEmissionsTotalRefPeriod",
      "diesel_emissions_total_ref_period",
      "emissions_total_ref_period_tco2e",
    )),
    notes: stringValue(fields.notes),
  };
}

export function mapRailUserRows(
  activities: ActivityDataOut[],
  defaults: RailUserRow[],
): RailUserRow[] {
  return defaults.map((defaultRow) => {
    const activity = activities.find((row) => row.extra_fields?.vehicle_type === defaultRow.vehicleType);
    return activity ? mapRailUserRow(activity, defaultRow) : defaultRow;
  });
}

