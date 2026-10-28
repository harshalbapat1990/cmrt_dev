import { beforeEach, describe, expect, it, vi } from "vitest";
import ActivityDataService from "@/services/ActivityData.service";
import { resolveTableConfig } from "./tableConfigRegistry";
import { createMitigationNewRowSaver } from "./mitigationNewRowSaver";

vi.mock("@/services/ActivityData.service", () => ({
  default: { createRow: vi.fn() },
}));
vi.mock("./tableConfigRegistry", () => ({
  resolveTableConfig: vi.fn(),
}));

describe("createMitigationNewRowSaver", () => {
  beforeEach(() => vi.clearAllMocks());

  const buildSaver = () => createMitigationNewRowSaver({
    projectId: "project-1",
    mitigationStageInstance: { id: "stage-1", stage: "CONSTRUCTION" },
    mitigationOptionId: "option-1",
    activePeriod: { id: "period-1" } as never,
    user: { user_id: "user-1", email: "user@example.com", first_name: "Rae", last_name: "User" } as never,
    resolveMetricId: vi.fn().mockResolvedValue("metric-1"),
    computeEmissionsForRow: vi.fn().mockResolvedValue({ total_emissions_tco2e: 5 }),
    apiRowToUiRow: vi.fn((row: { id: string }) => ({ id: row.id })),
    refreshOptionTotals: vi.fn().mockResolvedValue(undefined),
    mitigationActivityUsesSubmissionPeriod: () => true,
    constructionStartDate: null,
    constructionEndDate: null,
    opsStartYear: null,
    operationalLifeYears: null,
  });

  it("validates, saves and appends a mitigation row with its submission period", async () => {
    vi.mocked(resolveTableConfig).mockReturnValue({ rules: [] } as never);
    vi.mocked(ActivityDataService.createRow).mockResolvedValue({ id: "saved-1", extra_fields: {} } as never);
    const appendRow = vi.fn();
    const setError = vi.fn();

    await expect(buildSaver()(
      "bcDetailedLevel", "mitigation-1", { quantity: 3 }, appendRow, setError,
    )).resolves.toBe(true);

    expect(ActivityDataService.createRow).toHaveBeenCalledWith(expect.objectContaining({
      project_id: "project-1",
      project_stage_instance_id: "stage-1",
      project_option_id: "option-1",
      project_mitigation_id: "mitigation-1",
      submission_period_id: "period-1",
      ui_table_key: "bcDetailedLevel-mitigation",
    }));
    expect(appendRow).toHaveBeenCalledWith("bcDetailedLevel", expect.objectContaining({ id: "saved-1" }));
  });

  it("rejects rows missing required configured fields before saving", async () => {
    vi.mocked(resolveTableConfig).mockReturnValue({ rules: [{ key: "vehicle_type", required: true }] } as never);
    const setError = vi.fn();
    await expect(buildSaver()(
      "bcDetailedLevel", "mitigation-1", { quantity: 3 }, vi.fn(), setError,
    )).resolves.toBe(false);

    expect(setError).toHaveBeenCalledWith("Please enter required fields");
    expect(ActivityDataService.createRow).not.toHaveBeenCalled();
  });

  it("displays the saved server calculation instead of the optimistic preview", async () => {
    vi.mocked(resolveTableConfig).mockReturnValue({ rules: [] } as never);
    vi.mocked(ActivityDataService.createRow).mockResolvedValue({
      id: "saved-asset",
      emissions_tco2e: "24322.5",
      extra_fields: {},
    } as never);
    const saver = createMitigationNewRowSaver({
      projectId: "project-1",
      mitigationStageInstance: { id: "stage-1", stage: "CONSTRUCTION" },
      mitigationOptionId: "option-1",
      activePeriod: null,
      user: null,
      resolveMetricId: vi.fn().mockResolvedValue("metric-1"),
      computeEmissionsForRow: vi.fn().mockResolvedValue({ total_emissions_tco2e: 68550 }),
      apiRowToUiRow: vi.fn((row: { id: string; emissions_tco2e?: string }) => ({
        id: row.id,
        emissions_tco2e: row.emissions_tco2e,
      })),
      refreshOptionTotals: vi.fn().mockResolvedValue(undefined),
      mitigationActivityUsesSubmissionPeriod: () => false,
      constructionStartDate: null,
      constructionEndDate: null,
      opsStartYear: null,
      operationalLifeYears: null,
    });
    const appendRow = vi.fn();

    await expect(saver("asset", "mitigation-1", { quantity: 150000000 }, appendRow, vi.fn()))
      .resolves.toBe(true);

    expect(appendRow).toHaveBeenCalledWith("asset", expect.objectContaining({
      id: "saved-asset",
      emissions_tco2e: "24322.5",
      total_emissions_tco2e: "24322.5",
    }));
  });
});
