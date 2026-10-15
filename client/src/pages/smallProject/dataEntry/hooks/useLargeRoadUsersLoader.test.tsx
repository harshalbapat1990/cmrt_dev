import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ActivityDataService from "@/services/ActivityData.service";
import { useLargeRoadUsersLoader } from "./useLargeRoadUsersLoader";

vi.mock("@/services/ActivityData.service", () => ({
  default: { fetchRows: vi.fn() },
}));

describe("useLargeRoadUsersLoader", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(ActivityDataService.fetchRows).mockResolvedValue([]);
  });

  it("loads model parameters and vehicle rows using the selected scope", async () => {
    const setGlobalParams = vi.fn();
    const setYearData = vi.fn();
    const setEmissionSummary = vi.fn();
    renderHook(() => useLargeRoadUsersLoader({
      stageInstanceId: "stage-1",
      optionId: "option-1",
      projectMitigationId: "mitigation-1",
      scopeUiTableKey: (key) => `${key}-mitigation`,
      vehicleTypes: ["Small Car"],
      largeUsersYears: [2025],
      defaultParams: { ev_uptake_scenario: "Step Change", roughness: "Smooth", gradient: "Flat", curvature: "Straight" },
      setGlobalParams,
      setYearData,
      setEmissionSummary,
    }));

    await waitFor(() => expect(ActivityDataService.fetchRows).toHaveBeenCalledTimes(2));
    expect(ActivityDataService.fetchRows).toHaveBeenCalledWith(
      "stage-1", "largeRoadParams-mitigation", "option-1", undefined, "mitigation-1",
    );
    expect(ActivityDataService.fetchRows).toHaveBeenCalledWith(
      "stage-1", "largeRoadUsers-mitigation", "option-1", undefined, "mitigation-1",
    );
    expect(setGlobalParams).toHaveBeenCalledOnce();
    expect(setYearData).toHaveBeenCalledOnce();
    expect(setEmissionSummary).toHaveBeenCalledOnce();
  });
});
