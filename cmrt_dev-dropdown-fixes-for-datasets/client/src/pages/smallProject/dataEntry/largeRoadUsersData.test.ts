import { describe, expect, it } from "vitest";
import type { ActivityDataOut } from "@/services/ActivityData.service";
import {
  buildLargeRoadUserYears,
  buildLargeRoadUserPersistencePayloads,
  buildLargeAusRoadCalculationPayload,
  buildLargeNzRoadCalculationPayload,
} from "./largeRoadUsersData";

const activity = (
  id: string,
  extra_fields: ActivityDataOut["extra_fields"],
): ActivityDataOut => ({
  id,
  project_id: "project-1",
  project_stage_instance_id: "stage-1",
  quantity: 0,
  ui_table_key: "largeRoadUsers",
  extra_fields,
});

const defaults = {
  ev_uptake_scenario: "Step Change",
  roughness: "Smooth",
  gradient: "Flat",
  curvature: "Straight",
};

describe("buildLargeRoadUserYears", () => {
  it("maps stored rows and creates empty required years", () => {
    const result = buildLargeRoadUserYears(
      [activity("params", {
        modelled_year: 2030,
        ev_uptake_scenario: "Accelerated Transition",
        roughness: "Rough",
        interim_total_tco2e: 12,
      })],
      [activity("user", {
        modelled_year: 2030,
        vehicle_type: "Heavy Vehicle",
        vkt: 100,
        vht: 5,
        avg_speed: 20,
        last_edited: "vht",
      })],
      ["Heavy Vehicle", "Bus"],
      [2030, 2040],
      defaults,
    );

    expect(result.globalParams).toEqual({ ...defaults, ev_uptake_scenario: "Accelerated Transition", roughness: "Rough" });
    expect(result.summaryFields?.interim_total_tco2e).toBe(12);
    expect(result.years[2030].rows[0]).toMatchObject({
      id: "user",
      vehicleType: "Heavy Vehicle",
      vkt: "100",
      vht: "5",
      avgSpeed: "20",
      lastEdited: "vht",
    });
    expect(result.years[2030].rows[1].vehicleType).toBe("Bus");
    expect(result.years[2040].rows).toHaveLength(2);
  });

  it("uses defaults when there are no saved parameter rows", () => {
    const result = buildLargeRoadUserYears([], [], ["Bus"], [2025], defaults);
    expect(result.globalParams).toEqual(defaults);
    expect(result.summaryFields).toBeNull();
    expect(result.years[2025].rows[0].vehicleType).toBe("Bus");
  });
});

describe("buildLargeRoadUserPersistencePayloads", () => {
  it("creates scoped parameter rows and only persists users with numeric VKT", () => {
    const { paramsPayload, usersPayload } = buildLargeRoadUserPersistencePayloads({
      years: [2030, 2040],
      yearData: {
        2030: {
          params: defaults,
          rows: [
            { id: "row-1", vehicleType: "Bus", vkt: "1250", vht: "5", avgSpeed: "250", lastEdited: "vht", notes: "note" },
            { id: "row-2", vehicleType: "Truck", vkt: "", vht: "", avgSpeed: "", lastEdited: null, notes: "" },
          ],
        },
        2040: { params: defaults, rows: [] },
      },
      params: defaults,
      summary: { absoluteEmissions: 20, baseCaseAbsoluteEmissions: 25, relativeUserEmissions: -5 },
      projectId: "project-1",
      stageInstanceId: "stage-1",
      projectOptionId: "option-1",
      paramsTableKey: "largeRoadParams",
      usersTableKey: "largeRoadUsers",
      projectMitigationId: "mitigation-1",
    });

    expect(paramsPayload).toHaveLength(2);
    expect(paramsPayload[0]).toMatchObject({
      project_id: "project-1",
      project_mitigation_id: "mitigation-1",
      ui_table_key: "largeRoadParams",
      extra_fields: { modelled_year: 2030, interim_total_tco2e: 20 },
    });
    expect(usersPayload).toHaveLength(1);
    expect(usersPayload[0]).toMatchObject({
      quantity: 1250,
      project_option_id: "option-1",
      project_mitigation_id: "mitigation-1",
      ui_table_key: "largeRoadUsers",
      extra_fields: { modelled_year: 2030, vehicle_type: "Bus", vkt: "1250", vht: "5" },
    });
  });
});

describe("large road calculation payloads", () => {
  const yearData = {
    2030: {
      params: defaults,
      rows: [
        { id: "valid", vehicleType: "Heavy Vehicle", vkt: "100", vht: "5", avgSpeed: "", lastEdited: "vht" as const, notes: "" },
        { id: "incomplete", vehicleType: "Bus", vkt: "", vht: "", avgSpeed: "", lastEdited: null, notes: "" },
      ],
    },
  };
  const input = {
    years: [2025, 2030],
    yearData,
    projectId: "project-1",
    stageInstanceId: "stage-1",
    projectOptionId: "option-1",
  };

  it("uses NZ vehicle names and speed_kmh fields, omitting incomplete rows", () => {
    expect(buildLargeNzRoadCalculationPayload(input)).toEqual({
      project_id: "project-1",
      project_option_id: "option-1",
      project_stage_instance_id: "stage-1",
      anchor_years: [{
        year: 2030,
        vehicles: [{ vehicle_type: "heavy_vehicle", vkt: 100, speed_kmh: 20 }],
      }],
    });
  });

  it("includes Australian road parameters and average_speed_kph", () => {
    expect(buildLargeAusRoadCalculationPayload({ ...input, params: defaults })).toEqual({
      project_id: "project-1",
      project_option_id: "option-1",
      project_stage_instance_id: "stage-1",
      roughness: "Smooth",
      gradient: "Flat",
      curvature: "Straight",
      ev_uptake_scenario: "Step Change",
      anchor_years: [{
        year: 2030,
        vehicles: [{ vehicle_type: "Heavy Vehicle", vkt: 100, average_speed_kph: 20 }],
      }],
    });
  });

  it("returns null when no complete road rows are available", () => {
    expect(buildLargeNzRoadCalculationPayload({ ...input, yearData: {} })).toBeNull();
  });
});
