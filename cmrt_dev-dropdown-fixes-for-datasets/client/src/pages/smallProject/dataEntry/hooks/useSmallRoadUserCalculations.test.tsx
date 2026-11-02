import { act, renderHook } from "@testing-library/react";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { RoadUserRow } from "../roadUserTypes";
import type { UserCalculationSummary } from "../roadUserCalculations";
import { useSmallRoadUserCalculations } from "./useSmallRoadUserCalculations";

const { calculateRoadUserSummary } = vi.hoisted(() => ({ calculateRoadUserSummary: vi.fn() }));
vi.mock("../roadUserWorkflow", () => ({ calculateRoadUserSummary }));

const row: RoadUserRow = {
  id: "road-1",
  vehicleType: "Light vehicle",
  vkt: "120",
  vht: "6",
  avgSpeed: "20",
  lastEdited: "vht",
  notes: "",
};
const summary: UserCalculationSummary = {
  absoluteEmissions: 9,
  baseCaseAbsoluteEmissions: 12,
  relativeUserEmissions: -3,
};

describe("useSmallRoadUserCalculations", () => {
  beforeEach(() => vi.clearAllMocks());

  it("builds the AU payload and updates the summary after calculation", async () => {
    calculateRoadUserSummary.mockResolvedValue(summary);
    const { result } = renderHook(() => {
      const [currentSummary, setSummary] = useState<UserCalculationSummary>({
        absoluteEmissions: 0,
        baseCaseAbsoluteEmissions: 0,
        relativeUserEmissions: 0,
      });
      return {
        currentSummary,
        calculations: useSmallRoadUserCalculations({
          projectId: "project-1",
          stageInstanceId: "stage-1",
          projectOptionId: "option-1",
          region: "AU",
          showRoad: true,
          isLargeProject: false,
          setSummary,
        }),
      };
    });

    await act(async () => {
      await result.current.calculations.calculateSummary([row]);
    });

    expect(result.current.calculations.buildPayload([row])).toEqual({
      project_id: "project-1",
      project_option_id: "option-1",
      project_stage_instance_id: "stage-1",
      light_vehicle_vkt: 120,
      light_vehicle_speed_kmh: 20,
    });
    expect(calculateRoadUserSummary).toHaveBeenCalledWith(
      expect.objectContaining({ light_vehicle_vkt: 120 }),
      "AU",
      "small",
    );
    expect(result.current.currentSummary).toEqual(summary);
    expect(result.current.calculations.loading).toBe(false);
  });

  it.each([
    { showRoad: false, isLargeProject: false },
    { showRoad: true, isLargeProject: true },
  ])("skips calculation when road calculation is inapplicable (%o)", async (options) => {
    const { result } = renderHook(() => useSmallRoadUserCalculations({
      projectId: "project-1",
      stageInstanceId: "stage-1",
      region: "NZ",
      ...options,
      setSummary: vi.fn(),
    }));

    await act(async () => {
      await result.current.calculateSummary([row]);
    });

    expect(calculateRoadUserSummary).not.toHaveBeenCalled();
  });

  it("skips calculation when the rows do not produce a payload", async () => {
    const { result } = renderHook(() => useSmallRoadUserCalculations({
      projectId: "project-1",
      stageInstanceId: "stage-1",
      region: "NZ",
      showRoad: true,
      isLargeProject: false,
      setSummary: vi.fn(),
    }));

    await act(async () => {
      await result.current.calculateSummary([{ ...row, vkt: "", vht: "", avgSpeed: "" }]);
    });

    expect(calculateRoadUserSummary).not.toHaveBeenCalled();
  });

  it("returns no summary and clears loading when calculation fails", async () => {
    const error = new Error("calculation failed");
    calculateRoadUserSummary.mockRejectedValueOnce(error);
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const { result } = renderHook(() => useSmallRoadUserCalculations({
      projectId: "project-1",
      stageInstanceId: "stage-1",
      region: "NZ",
      showRoad: true,
      isLargeProject: false,
      setSummary: vi.fn(),
    }));

    let summaryResult: UserCalculationSummary | null = summary;
    await act(async () => {
      summaryResult = await result.current.calculateSummary([row]);
    });

    expect(summaryResult).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(errorSpy).toHaveBeenCalledWith("Failed to calculate road user emissions:", error);
    errorSpy.mockRestore();
  });
});
