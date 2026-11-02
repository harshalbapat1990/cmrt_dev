import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { RoadUserRow } from "../roadUserTypes";
import type { UserCalculationSummary } from "../roadUserCalculations";
import { useSmallRoadUserSave } from "./useSmallRoadUserSave";

const row: RoadUserRow = {
  id: "road-1",
  vehicleType: "Light vehicle",
  vkt: "100",
  vht: "5",
  avgSpeed: "20",
  lastEdited: "vht",
  notes: "",
};
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

function createParams(overrides: Partial<Parameters<typeof useSmallRoadUserSave>[0]> = {}) {
  return {
    readOnly: false,
    rows: [row],
    currentSummary,
    buildPayload: vi.fn(() => ({ road: "payload" })),
    calculateSummary: vi.fn(async () => calculatedSummary),
    persistRows: vi.fn(async () => undefined),
    ...overrides,
  };
}

describe("useSmallRoadUserSave", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calculates emissions before saving rows with a valid calculation payload", async () => {
    const params = createParams();
    const { result } = renderHook(() => useSmallRoadUserSave(params));

    await act(async () => result.current());

    expect(params.buildPayload).toHaveBeenCalledWith([row]);
    expect(params.calculateSummary).toHaveBeenCalledWith([row]);
    expect(params.persistRows).toHaveBeenCalledWith([row], calculatedSummary);
  });

  it("saves the existing summary when there is no calculation payload", async () => {
    const params = createParams({ buildPayload: vi.fn(() => null) });
    const { result } = renderHook(() => useSmallRoadUserSave(params));

    await act(async () => result.current());

    expect(params.calculateSummary).not.toHaveBeenCalled();
    expect(params.persistRows).toHaveBeenCalledWith([row], currentSummary);
  });

  it("does not persist when a required calculation returns no summary", async () => {
    const params = createParams({ calculateSummary: vi.fn(async () => null) });
    const { result } = renderHook(() => useSmallRoadUserSave(params));

    await act(async () => result.current());

    expect(params.persistRows).not.toHaveBeenCalled();
  });

  it("does not calculate or persist in read-only mode", async () => {
    const params = createParams({ readOnly: true });
    const { result } = renderHook(() => useSmallRoadUserSave(params));

    await act(async () => result.current());

    expect(params.calculateSummary).not.toHaveBeenCalled();
    expect(params.persistRows).not.toHaveBeenCalled();
  });

  it("contains save errors without leaving an unhandled rejection", async () => {
    const error = new Error("save failed");
    const params = createParams({ persistRows: vi.fn(async () => { throw error; }) });
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const { result } = renderHook(() => useSmallRoadUserSave(params));

    await act(async () => result.current());

    expect(errorSpy).toHaveBeenCalledWith("Failed to save road users data:", error);
    errorSpy.mockRestore();
  });
});
