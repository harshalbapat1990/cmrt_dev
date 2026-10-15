import { beforeEach, describe, expect, it, vi } from "vitest";
import ActivityDataService from "@/services/ActivityData.service";
import { createMitigationTableUploader } from "./mitigationTableUploader";

vi.mock("@/services/ActivityData.service", () => ({
  default: { bulkUpsert: vi.fn(), createRow: vi.fn() },
}));

describe("createMitigationTableUploader", () => {
  beforeEach(() => vi.clearAllMocks());

  const buildUploader = (activePeriod: { id: string } | null = { id: "period-1" }) => ({
    uploader: createMitigationTableUploader({
      projectId: "project-1",
      mitigationStageInstance: { id: "stage-1", stage: "CONSTRUCTION" },
      mitigationOptionId: "option-1",
      activePeriod: activePeriod as never,
      user: { email: "editor@example.com", first_name: "Rae", last_name: "User" } as never,
      operationalLifeYears: 40,
      mitigationActivityUsesSubmissionPeriod: () => true,
      resolveMetricId: vi.fn().mockResolvedValue("metric-1"),
      computeEmissionsForRow: vi.fn().mockResolvedValue({ total_emissions_tco2e: 6 }),
      apiRowToUiRow: vi.fn((row: { id: string }) => ({ id: row.id })),
      refreshOptionTotals: vi.fn().mockResolvedValue(undefined),
      constructionStartDate: null,
      constructionEndDate: null,
      opsStartYear: null,
    }),
    refreshOptionTotals: vi.fn(),
  });

  it("calculates and bulk-saves validated rows with mitigation scope", async () => {
    vi.mocked(ActivityDataService.bulkUpsert).mockResolvedValue([]);
    const { uploader } = buildUploader();

    await expect(uploader("bcDetailedLevel", "mitigation-1", [{ quantity: 2 }]))
      .resolves.toEqual({ rows: [] });

    expect(ActivityDataService.bulkUpsert).toHaveBeenCalledWith(
      "stage-1",
      "bcDetailedLevel-mitigation",
      [expect.objectContaining({
        project_id: "project-1",
        project_option_id: "option-1",
        project_mitigation_id: "mitigation-1",
        submission_period_id: "period-1",
        total_emissions_tco2e: 6,
      })],
      "mitigation-1",
    );
  });

  it("rejects construction uploads without an active period", async () => {
    const { uploader } = buildUploader(null);

    await expect(uploader("constructionG2", "mitigation-1", []))
      .rejects.toThrow("No active construction period selected.");
    expect(ActivityDataService.bulkUpsert).not.toHaveBeenCalled();
  });

  it("rejects electricity uploads whose years cannot be calculated", async () => {
    const { uploader } = buildUploader();

    await expect(uploader("electricity", "mitigation-1", [{
      emission_source: "Grid electricity",
      year: 2025,
      quantity_mwh: 3,
    }])).rejects.toThrow("Construction start and end year are required for electricity calculations.");
    expect(ActivityDataService.bulkUpsert).not.toHaveBeenCalled();
  });

  it("rejects replacement rows whose life exceeds the project life", async () => {
    const { uploader } = buildUploader();

    await expect(uploader("componentRepl", "mitigation-1", [{ life: 40 }]))
      .rejects.toThrow("Row 1: Life (years) must be less than or equal to the operational life of project (40 years).");
    expect(ActivityDataService.bulkUpsert).not.toHaveBeenCalled();
  });
});
