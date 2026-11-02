import { describe, expect, it } from "vitest";
import type { ActivityDataOut } from "@/services/ActivityData.service";
import { activityToRoadUserRow } from "./roadUserMapping";

const activity = (extra_fields: ActivityDataOut["extra_fields"]): ActivityDataOut => ({
  id: "activity-1",
  project_id: "project-1",
  project_stage_instance_id: "stage-1",
  quantity: 0,
  ui_table_key: "roadUsers",
  extra_fields,
});

describe("activityToRoadUserRow", () => {
  it("maps persisted fields into the shared editable row shape", () => {
    expect(activityToRoadUserRow(activity({
      vkt: 125,
      vht: "42",
      avg_speed: 60,
      last_edited: "vht",
      notes: "surveyed",
    }), "Heavy vehicle", "fallback")).toEqual({
      id: "activity-1",
      vehicleType: "Heavy vehicle",
      vkt: "125",
      vht: "42",
      avgSpeed: "60",
      lastEdited: "vht",
      notes: "surveyed",
    });
  });

  it("uses empty values for missing data and ignores an invalid last-edited value", () => {
    const row = activityToRoadUserRow(activity(null), "Light vehicle", "road-1");
    expect(row).toEqual({
      id: "activity-1",
      vehicleType: "Light vehicle",
      vkt: "",
      vht: "",
      avgSpeed: "",
      lastEdited: null,
      notes: "",
    });
  });
});
