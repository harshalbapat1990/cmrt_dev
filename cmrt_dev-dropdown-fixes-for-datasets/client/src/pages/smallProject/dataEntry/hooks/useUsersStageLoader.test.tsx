import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ActivityDataService from "@/services/ActivityData.service";
import { useUsersStageLoader } from "./useUsersStageLoader";

vi.mock("@/services/ActivityData.service", () => ({
  default: { fetchRows: vi.fn() },
}));

describe("useUsersStageLoader", () => {
  beforeEach(() => vi.clearAllMocks());

  it("loads both user tables with option and mitigation scope", async () => {
    vi.mocked(ActivityDataService.fetchRows).mockResolvedValue([]);
    const setRoadRows = vi.fn();
    const setRailRows = vi.fn();
    const setRoadSummary = vi.fn();
    const scopeUiTableKey = (key: string) => `${key}-mitigation`;
    renderHook(() => useUsersStageLoader({
      stageInstanceId: "stage-1",
      optionId: "option-1",
      refreshKey: 2,
      projectMitigationId: "mitigation-1",
      scopeUiTableKey,
      roadVehicleTypes: ["Light vehicle"],
      initialRailRows: [],
      setRoadRows,
      setRailRows,
      setRoadSummary,
    }));

    await waitFor(() => expect(ActivityDataService.fetchRows).toHaveBeenCalledTimes(2));
    expect(ActivityDataService.fetchRows).toHaveBeenCalledWith(
      "stage-1", "roadUsers-mitigation", "option-1", undefined, "mitigation-1",
    );
    expect(ActivityDataService.fetchRows).toHaveBeenCalledWith(
      "stage-1", "railUsers-mitigation", "option-1", undefined, "mitigation-1",
    );
    expect(setRoadRows).toHaveBeenCalledOnce();
    expect(setRailRows).toHaveBeenCalledOnce();
    expect(setRoadSummary).toHaveBeenCalledOnce();
  });
});
