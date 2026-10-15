import { beforeEach, describe, expect, it, vi } from "vitest";
import ActivityDataService from "@/services/ActivityData.service";
import { saveMitigationBulkTable } from "./mitigationBulkPersistence";

vi.mock("@/services/ActivityData.service", () => ({
  default: { bulkUpsert: vi.fn() },
}));

describe("saveMitigationBulkTable", () => {
  beforeEach(() => vi.clearAllMocks());

  it("persists calculated rows with mitigation and construction-period scope", async () => {
    const refreshOptionTotals = vi.fn().mockResolvedValue(undefined);
    const computeEmissions = vi.fn().mockResolvedValue({ total_emissions_tco2e: 3 });
    await saveMitigationBulkTable({
      baseKey: "constructionG2",
      projectMitigationId: "mitigation-1",
      rows: [{ quantity: 2, _fromApi: true }],
      projectId: "project-1",
      stageInstanceId: "stage-1",
      projectOptionId: "option-1",
      activePeriod: { id: "period-1" } as never,
      shouldUseSubmissionPeriod: () => true,
      computeEmissions,
      refreshOptionTotals,
    });

    expect(computeEmissions).toHaveBeenCalledWith("constructionG2", { quantity: 2, _fromApi: true });
    expect(ActivityDataService.bulkUpsert).toHaveBeenCalledWith(
      "stage-1",
      "constructionG2-mitigation",
      [expect.objectContaining({
        project_id: "project-1",
        project_option_id: "option-1",
        project_mitigation_id: "mitigation-1",
        submission_period_id: "period-1",
        total_emissions_tco2e: 3,
        extra_fields: expect.not.objectContaining({ _fromApi: true }),
      })],
      "mitigation-1",
    );
    expect(refreshOptionTotals).toHaveBeenCalledOnce();
  });

  it("skips a construction save when no period is selected", async () => {
    const computeEmissions = vi.fn();
    await saveMitigationBulkTable({
      baseKey: "constructionG3",
      projectMitigationId: "mitigation-1",
      rows: [],
      projectId: "project-1",
      stageInstanceId: "stage-1",
      projectOptionId: null,
      activePeriod: null,
      shouldUseSubmissionPeriod: () => false,
      computeEmissions,
      refreshOptionTotals: vi.fn(),
    });

    expect(computeEmissions).not.toHaveBeenCalled();
    expect(ActivityDataService.bulkUpsert).not.toHaveBeenCalled();
  });

  it("propagates persistence failures and does not report totals as refreshed", async () => {
    const persistenceError = new Error("Mitigation save failed");
    vi.mocked(ActivityDataService.bulkUpsert).mockRejectedValueOnce(persistenceError);
    const refreshOptionTotals = vi.fn().mockResolvedValue(undefined);

    await expect(saveMitigationBulkTable({
      baseKey: "component",
      projectMitigationId: "mitigation-1",
      rows: [{ quantity: 2 }],
      projectId: "project-1",
      stageInstanceId: "stage-1",
      projectOptionId: "option-1",
      activePeriod: null,
      shouldUseSubmissionPeriod: () => false,
      computeEmissions: vi.fn().mockResolvedValue(null),
      refreshOptionTotals,
    })).rejects.toBe(persistenceError);

    expect(refreshOptionTotals).not.toHaveBeenCalled();
  });
});
