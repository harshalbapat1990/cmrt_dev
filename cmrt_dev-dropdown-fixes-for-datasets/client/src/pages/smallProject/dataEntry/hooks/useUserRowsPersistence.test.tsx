import { act, renderHook } from "@testing-library/react";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ActivityDataService from "@/services/ActivityData.service";
import type { ActivityDataCreate } from "@/services/ActivityData.service";
import type { RoadUserRow } from "../roadUserTypes";
import { useUserRowsPersistence } from "./useUserRowsPersistence";

const { bulkUpsert } = vi.hoisted(() => ({ bulkUpsert: vi.fn() }));
vi.mock("@/services/ActivityData.service", () => ({
  default: { bulkUpsert },
}));

const row: RoadUserRow = {
  id: "draft-1",
  vehicleType: "Bus",
  vkt: "10",
  vht: "2",
  avgSpeed: "5",
  lastEdited: "vht",
  notes: "",
};

describe("useUserRowsPersistence", () => {
  beforeEach(() => vi.clearAllMocks());

  it("persists rows, reconciles returned ids, and refreshes totals", async () => {
    bulkUpsert.mockResolvedValueOnce([
      { id: "saved-1", extra_fields: { vehicle_type: "Bus" } },
    ]);
    const onTotalsUpdated = vi.fn(async () => undefined);
    const payload: ActivityDataCreate[] = [{
      project_id: "project-1",
      project_stage_instance_id: "stage-1",
      project_option_id: "option-1",
      metric_id: null,
      quantity: 10,
      unit_id: null,
      ui_table_key: "roadUsers::mitigation-1",
      extra_fields: { vehicle_type: "Bus" },
    }];
    const { result } = renderHook(() => {
      const [rows, setRows] = useState([row]);
      const persistence = useUserRowsPersistence({
        readOnly: false,
        stageInstanceId: "stage-1",
        tableKey: "roadUsers::mitigation-1",
        projectMitigationId: "mitigation-1",
        setRows,
        buildPayload: () => payload,
        onTotalsUpdated,
        errorLabel: "road users data",
      });
      return { rows, persistence };
    });

    await act(async () => result.current.persistence.persistRows([row]));

    expect(ActivityDataService.bulkUpsert).toHaveBeenCalledWith(
      "stage-1",
      "roadUsers::mitigation-1",
      payload,
      "mitigation-1",
    );
    expect(result.current.rows[0].id).toBe("saved-1");
    expect(result.current.persistence.saveState).toBe("saved");
    expect(onTotalsUpdated).toHaveBeenCalledOnce();
  });

  it("does not call the API when the editor is read-only", async () => {
    const { result } = renderHook(() => {
      const [rows, setRows] = useState([row]);
      return {
        rows,
        persistence: useUserRowsPersistence({
          readOnly: true,
          stageInstanceId: "stage-1",
          tableKey: "roadUsers",
          projectMitigationId: null,
          setRows,
          buildPayload: () => [],
          errorLabel: "road users data",
        }),
      };
    });

    await act(async () => result.current.persistence.persistRows([row]));

    expect(ActivityDataService.bulkUpsert).not.toHaveBeenCalled();
    expect(result.current.persistence.saveState).toBe("idle");
  });

  it("returns to idle and skips totals refresh when a save fails", async () => {
    const error = new Error("save failed");
    bulkUpsert.mockRejectedValueOnce(error);
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const onTotalsUpdated = vi.fn();
    const { result } = renderHook(() => {
      const [rows, setRows] = useState([row]);
      const persistence = useUserRowsPersistence({
        readOnly: false,
        stageInstanceId: "stage-1",
        tableKey: "roadUsers",
        projectMitigationId: null,
        setRows,
        buildPayload: () => [{
          project_id: "project-1",
          project_stage_instance_id: "stage-1",
          project_option_id: null,
          metric_id: null,
          quantity: 10,
          unit_id: null,
          ui_table_key: "roadUsers",
          extra_fields: { vehicle_type: "Bus" },
        }],
        onTotalsUpdated,
        errorLabel: "road users data",
      });
      return { rows, persistence };
    });

    await act(async () => result.current.persistence.persistRows([row]));

    expect(result.current.rows).toEqual([row]);
    expect(result.current.persistence.saveState).toBe("idle");
    expect(onTotalsUpdated).not.toHaveBeenCalled();
    expect(errorSpy).toHaveBeenCalledWith("Failed to save road users data:", error);
    errorSpy.mockRestore();
  });
});
