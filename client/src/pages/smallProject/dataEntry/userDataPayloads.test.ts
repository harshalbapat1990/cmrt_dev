import { describe, expect, it } from "vitest";
import { buildRailActivityPayload, buildRoadActivityPayload, buildRoadCalculationPayload } from "./userDataPayloads";
import type { RoadUserRow } from "./roadUserTypes";
import type { RailUserRow } from "./userDataMapping";

const context = {
  projectId: "project-1",
  stageInstanceId: "stage-1",
  projectOptionId: "option-1",
  projectMitigationId: "mitigation-1",
};

const roadRows: RoadUserRow[] = [
  { id: "row-1", vehicleType: " Light Vehicle ", vkt: "120", vht: "6", avgSpeed: "", lastEdited: "vht", notes: "note" },
  { id: "row-2", vehicleType: "Heavy vehicle", vkt: "", vht: "", avgSpeed: "", lastEdited: null, notes: "" },
];

describe("user data payloads", () => {
  it("builds calculation payloads from complete road rows", () => {
    expect(buildRoadCalculationPayload(roadRows, context)).toEqual({
      project_id: "project-1",
      project_option_id: "option-1",
      project_stage_instance_id: "stage-1",
      light_vehicle_vkt: 120,
      light_vehicle_speed_kmh: 20,
    });
    expect(buildRoadCalculationPayload([], context)).toBeNull();
  });

  it("persists only road rows with valid VKT and includes the emissions summary", () => {
    const result = buildRoadActivityPayload(roadRows, context, "roadUsers", {
      absoluteEmissions: 10,
      baseCaseAbsoluteEmissions: 8,
      relativeUserEmissions: 2,
    });
    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      project_id: "project-1",
      project_stage_instance_id: "stage-1",
      project_option_id: "option-1",
      project_mitigation_id: "mitigation-1",
      ui_table_key: "roadUsers",
      quantity: 120,
      extra_fields: {
        vehicle_type: " Light Vehicle ",
        absoluteEmissions: 10,
        absolute_emissions: 10,
        baseCaseAbsoluteEmissions: 8,
        relative_user_emissions: 2,
      },
    });
  });

  it("builds rail activity rows with optional year and safe numeric quantity", () => {
    const row: RailUserRow = {
      id: "rail-1",
      vehicleType: "Container Train",
      terrain: "Flat",
      freight: "12.5",
      dieselEmissionsIntensity: "3",
      dieselEmissions: "4",
      dieselEmissionsTotalRefPeriod: "5",
      notes: "surveyed",
    };
    const payload = buildRailActivityPayload([row], context, "railUsers", 2030);
    expect(payload[0]).toMatchObject({
      quantity: 12.5,
      ui_table_key: "railUsers",
      project_mitigation_id: "mitigation-1",
      extra_fields: {
        modelled_year: 2030,
        vehicle_type: "Container Train",
        emissions_intensity_tco2e_kl: "3",
        emissions_annual_tco2e: "4",
        emissions_total_ref_period_tco2e: "5",
      },
    });
    expect(buildRailActivityPayload([{ ...row, freight: "invalid" }], context, "railUsers")[0].quantity).toBe(0);
  });
});
