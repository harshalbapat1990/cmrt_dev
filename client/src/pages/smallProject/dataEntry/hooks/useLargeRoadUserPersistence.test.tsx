import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ActivityDataService from "@/services/ActivityData.service";
import type { RoadParams, RoadUserYearData } from "../roadUserTypes";
import type { UserCalculationSummary } from "../roadUserCalculations";
import { useLargeRoadUserPersistence } from "./useLargeRoadUserPersistence";

const { bulkUpsert } = vi.hoisted(() => ({ bulkUpsert: vi.fn() }));
vi.mock("@/services/ActivityData.service", () => ({ default: { bulkUpsert } }));

const params: RoadParams = {
  ev_uptake_scenario: "Step Change",
  roughness: "Smooth",
  gradient: "Flat",
  curvature: "Straight",
};
const summary: UserCalculationSummary = {
  absoluteEmissions: 12,
  baseCaseAbsoluteEmissions: 20,
  relativeUserEmissions: 8,
};
const yearData: Record<number, RoadUserYearData> = {
  2030: {
    params,
    rows: [{
      id: "draft-1",
      vehicleType: "Bus",
      vkt: "10",
      vht: "2",
      avgSpeed: "5",
      lastEdited: "vht",
      notes: "",
    }],
  },
};

describe("useLargeRoadUserPersistence", () => {
  beforeEach(() => vi.clearAllMocks());

  it("persists parameters before user rows and then refreshes totals", async () => {
    const calls: string[] = [];
    bulkUpsert.mockImplementation(async (_stage: string, tableKey: string) => {
      calls.push(tableKey);
      return [];
    });
    const onTotalsUpdated = vi.fn(async () => { calls.push("totals"); });
    const { result } = renderHook(() => useLargeRoadUserPersistence({
      readOnly: false,
      stageInstanceId: "stage-1",
      projectId: "project-1",
      projectOptionId: "option-1",
      projectMitigationId: "mitigation-1",
      paramsTableKey: "largeRoadParams::mitigation-1",
      usersTableKey: "largeRoadUsers::mitigation-1",
      getModelledYears: () => [2030],
      defaultParams: params,
      defaultSummary: summary,
      onTotalsUpdated,
    }));

    await act(async () => result.current.persistAll(yearData));

    expect(ActivityDataService.bulkUpsert).toHaveBeenNthCalledWith(
      1,
      "stage-1",
      "largeRoadParams::mitigation-1",
      expect.arrayContaining([expect.objectContaining({
        project_id: "project-1",
        project_option_id: "option-1",
        project_mitigation_id: "mitigation-1",
        extra_fields: expect.objectContaining({ modelled_year: 2030, interim_total_tco2e: 12 }),
      })]),
      "mitigation-1",
    );
    expect(ActivityDataService.bulkUpsert).toHaveBeenNthCalledWith(
      2,
      "stage-1",
      "largeRoadUsers::mitigation-1",
      expect.arrayContaining([expect.objectContaining({
        quantity: 10,
        extra_fields: expect.objectContaining({ modelled_year: 2030, vehicle_type: "Bus" }),
      })]),
      "mitigation-1",
    );
    expect(calls).toEqual([
      "largeRoadParams::mitigation-1",
      "largeRoadUsers::mitigation-1",
      "totals",
    ]);
    expect(result.current.saveState).toBe("saved");
  });

  it("does not write or refresh totals in read-only mode", async () => {
    const onTotalsUpdated = vi.fn();
    const { result } = renderHook(() => useLargeRoadUserPersistence({
      readOnly: true,
      stageInstanceId: "stage-1",
      projectId: "project-1",
      projectMitigationId: null,
      paramsTableKey: "largeRoadParams",
      usersTableKey: "largeRoadUsers",
      getModelledYears: () => [2030],
      defaultParams: params,
      defaultSummary: summary,
      onTotalsUpdated,
    }));

    await act(async () => result.current.persistAll(yearData));

    expect(ActivityDataService.bulkUpsert).not.toHaveBeenCalled();
    expect(onTotalsUpdated).not.toHaveBeenCalled();
    expect(result.current.saveState).toBe("idle");
  });

  it("returns to idle and skips totals refresh when a persistence write fails", async () => {
    const error = new Error("write failed");
    bulkUpsert.mockRejectedValueOnce(error);
    const onTotalsUpdated = vi.fn();
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const { result } = renderHook(() => useLargeRoadUserPersistence({
      readOnly: false,
      stageInstanceId: "stage-1",
      projectId: "project-1",
      projectMitigationId: null,
      paramsTableKey: "largeRoadParams",
      usersTableKey: "largeRoadUsers",
      getModelledYears: () => [2030],
      defaultParams: params,
      defaultSummary: summary,
      onTotalsUpdated,
    }));

    await act(async () => result.current.persistAll(yearData));

    expect(result.current.saveState).toBe("idle");
    expect(onTotalsUpdated).not.toHaveBeenCalled();
    expect(errorSpy).toHaveBeenCalledWith("Failed to save large road users data:", error);
    errorSpy.mockRestore();
  });
});
