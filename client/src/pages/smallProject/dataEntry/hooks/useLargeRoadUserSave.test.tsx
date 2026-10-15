import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { RoadParams, RoadUserYearData } from "../roadUserTypes";
import type { UserCalculationSummary } from "../roadUserCalculations";
import { useLargeRoadUserSave } from "./useLargeRoadUserSave";

const params: RoadParams = {
  ev_uptake_scenario: "Step Change",
  roughness: "Smooth",
  gradient: "Flat",
  curvature: "Straight",
};
const yearData: Record<number, RoadUserYearData> = { 2030: { params, rows: [] } };
const currentSummary: UserCalculationSummary = {
  absoluteEmissions: 10,
  baseCaseAbsoluteEmissions: 12,
  relativeUserEmissions: -2,
};
const calculatedSummary: UserCalculationSummary = {
  absoluteEmissions: 8,
  baseCaseAbsoluteEmissions: 12,
  relativeUserEmissions: -4,
};

describe("useLargeRoadUserSave", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calculates for the selected region before persisting the refreshed summary", async () => {
    const calculateSummary = vi.fn(async () => calculatedSummary);
    const persistAll = vi.fn(async () => undefined);
    const save = renderHook(() => useLargeRoadUserSave({
      readOnly: false,
      region: "NZ",
      yearData,
      roadParams: params,
      currentSummary,
      calculateSummary,
      persistAll,
    })).result;

    await act(async () => save.current());

    expect(calculateSummary).toHaveBeenCalledWith(yearData, "NZ", params);
    expect(persistAll).toHaveBeenCalledWith(yearData, params, calculatedSummary);
  });

  it("persists the existing summary when no calculation result is available", async () => {
    const calculateSummary = vi.fn(async () => null);
    const persistAll = vi.fn(async () => undefined);
    const { result } = renderHook(() => useLargeRoadUserSave({
      readOnly: false,
      region: "AU",
      yearData,
      roadParams: params,
      currentSummary,
      calculateSummary,
      persistAll,
    }));

    await act(async () => result.current());

    expect(persistAll).toHaveBeenCalledWith(yearData, params, currentSummary);
  });

  it("does not calculate or persist in read-only mode", async () => {
    const calculateSummary = vi.fn(async () => calculatedSummary);
    const persistAll = vi.fn(async () => undefined);
    const { result } = renderHook(() => useLargeRoadUserSave({
      readOnly: true,
      region: "AU",
      yearData,
      roadParams: params,
      currentSummary,
      calculateSummary,
      persistAll,
    }));

    await act(async () => result.current());

    expect(calculateSummary).not.toHaveBeenCalled();
    expect(persistAll).not.toHaveBeenCalled();
  });
});
