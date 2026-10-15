import { describe, expect, it } from "vitest";
import type { ActivityDataOut } from "@/services/ActivityData.service";
import { mapRailUserRows, mapRoadUserRows, type RailUserRow } from "./userDataMapping";

const activity = (
  id: string,
  vehicleType: string,
  fields: Record<string, unknown>,
): ActivityDataOut => ({
  id,
  project_id: "project-1",
  project_stage_instance_id: "stage-1",
  quantity: 0,
  ui_table_key: "users",
  extra_fields: { ...fields, vehicle_type: vehicleType },
});

describe("user data mapping", () => {
  it("maps road rows by vehicle type and gives each empty row a stable ID", () => {
    const rows = mapRoadUserRows(
      [activity("heavy-row", "Heavy vehicle", { vkt: 250, avg_speed: 50 })],
      ["Light vehicle", "Heavy vehicle", "Bus"],
    );

    expect(rows.map((row) => row.id)).toEqual(["road-1", "heavy-row", "road-3"]);
    expect(rows[1]).toMatchObject({ vehicleType: "Heavy vehicle", vkt: "250", avgSpeed: "50" });
    expect(rows[2].vkt).toBe("");
  });

  it("maps legacy rail field aliases and fills rows with defaults", () => {
    const defaults: RailUserRow[] = [
      {
        id: "rail-1",
        vehicleType: "Container Train",
        terrain: "Flat",
        freight: "",
        dieselEmissionsIntensity: "",
        dieselEmissions: "",
        dieselEmissionsTotalRefPeriod: "",
        notes: "",
      },
      {
        id: "rail-2",
        vehicleType: "Grain Train",
        terrain: "Hilly",
        freight: "",
        dieselEmissionsIntensity: "",
        dieselEmissions: "",
        dieselEmissionsTotalRefPeriod: "",
        notes: "",
      },
    ];

    const rows = mapRailUserRows([
      activity("saved-rail", "Container Train", {
        terrain: "Curvy",
        freight: 12,
        diesel_emissions_intensity: 3.5,
        emissions_annual_tco2e: 7,
        emissions_total_ref_period_tco2e: 21,
        notes: "measured",
      }),
    ], defaults);

    expect(rows[0]).toMatchObject({
      id: "saved-rail",
      terrain: "Curvy",
      freight: "12",
      dieselEmissionsIntensity: "3.5",
      dieselEmissions: "7",
      dieselEmissionsTotalRefPeriod: "21",
      notes: "measured",
    });
    expect(rows[1]).toBe(defaults[1]);
  });
});
