import { act, renderHook } from "@testing-library/react";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { RoadUserYearData } from "../roadUserTypes";
import type { UserCalculationSummary } from "../roadUserCalculations";
import { useLargeRoadUserCalculations } from "./useLargeRoadUserCalculations";

const { calculateRoadUserSummary } = vi.hoisted(() => ({ calculateRoadUserSummary: vi.fn() }));
vi.mock("../roadUserWorkflow", () => ({ calculateRoadUserSummary }));

const yearData: Record<number, RoadUserYearData> = {
  2030: {
    params: { ev_uptake_scenario: "Step Change", roughness: "Smooth", gradient: "Flat", curvature: "Straight" },
    rows: [{
      id: "road-1",
      vehicleType: "Bus",
      vkt: "100",
      vht: "5",
      avgSpeed: "20",
      lastEdited: "vht",
      notes: "",
    }],
  },
};
const summary: UserCalculationSummary = {
  absoluteEmissions: 10,
  baseCaseAbsoluteEmissions: 15,
  relativeUserEmissions: -5,
};

describe("useLargeRoadUserCalculations", () => {
  beforeEach(() => vi.clearAllMocks());

  it("uses the AU large calculation and publishes its summary", async () => {
    calculateRoadUserSummary.mockResolvedValue(summary);
    const { result } = renderHook(() => {
      const [currentSummary, setSummary] = useState<UserCalculationSummary>({
        absoluteEmissions: 0,
        baseCaseAbsoluteEmissions: 0,
        relativeUserEmissions: 0,
      });
      const calculations = useLargeRoadUserCalculations({
        projectId: "project-1",
        stageInstanceId: "stage-1",
        projectOptionId: "option-1",
        getModelledYears: () => [2030],
        setSummary,
      });
      return { currentSummary, calculations };
    });

    await act(async () => {
      await result.current.calculations.calculateSummary(yearData, "AU", yearData[2030].params);
    });

    expect(calculateRoadUserSummary).toHaveBeenCalledWith(expect.objectContaining({
      project_id: "project-1",
      anchor_years: [{ year: 2030, vehicles: [expect.objectContaining({ vehicle_type: "Bus" })] }],
    }), "AU", "large");
    expect(result.current.currentSummary).toEqual(summary);
    expect(result.current.calculations.loading).toBe(false);
  });

  it("skips the API when there are no complete rows", async () => {
    const { result } = renderHook(() => useLargeRoadUserCalculations({
      projectId: "project-1",
      stageInstanceId: "stage-1",
      getModelledYears: () => [2030],
      setSummary: vi.fn(),
    }));

    await act(async () => {
      await result.current.calculateSummary({ 2030: { ...yearData[2030], rows: [] } }, "NZ", yearData[2030].params);
    });

    expect(calculateRoadUserSummary).not.toHaveBeenCalled();
    expect(result.current.loading).toBe(false);
  });

  it("returns no summary and clears loading when the large calculation fails", async () => {
    const error = new Error("large calculation failed");
    calculateRoadUserSummary.mockRejectedValueOnce(error);
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const { result } = renderHook(() => useLargeRoadUserCalculations({
      projectId: "project-1",
      stageInstanceId: "stage-1",
      getModelledYears: () => [2030],
      setSummary: vi.fn(),
    }));

    let summaryResult: UserCalculationSummary | null = summary;
    await act(async () => {
      summaryResult = await result.current.calculateSummary(yearData, "NZ", yearData[2030].params);
    });

    expect(summaryResult).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(errorSpy).toHaveBeenCalledWith("NZ road calculation failed:", error);
    errorSpy.mockRestore();
  });
});
