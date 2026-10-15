import { beforeEach, describe, expect, it, vi } from "vitest";
import ActivityDataService from "@/services/ActivityData.service";
import { saveSimplifiedConcreteMixRow } from "./saveSimplifiedConcreteMixRow";

vi.mock("@/services/ActivityData.service", () => ({
  default: { createRow: vi.fn() },
}));

describe("saveSimplifiedConcreteMixRow", () => {
  beforeEach(() => vi.clearAllMocks());

  const dependencies = () => ({
    draft: { volume: 12, mixType: "standard" },
    projectId: "project-1",
    stageInstanceId: "stage-1",
    projectOptionId: "option-1",
    computeEmissions: vi.fn().mockResolvedValue({ total_emissions_tco2e: 4.5 }),
    apiRowToUiRow: vi.fn((row: { id: string }) => ({ id: row.id })),
    appendRow: vi.fn(),
    setError: vi.fn(),
    refreshOptionTotals: vi.fn().mockResolvedValue(undefined),
  });

  it("calculates, persists and appends a simplified mix", async () => {
    const deps = dependencies();
    vi.mocked(ActivityDataService.createRow).mockResolvedValue({ id: "row-1" } as never);

    await expect(saveSimplifiedConcreteMixRow(deps)).resolves.toBe(true);

    expect(ActivityDataService.createRow).toHaveBeenCalledWith(expect.objectContaining({
      project_id: "project-1",
      project_stage_instance_id: "stage-1",
      quantity: 12,
      ui_table_key: "concreteRegSimplified",
      emissions_tco2e: 4.5,
    }));
    expect(deps.appendRow).toHaveBeenCalledWith({ id: "row-1" });
    expect(deps.refreshOptionTotals).toHaveBeenCalledOnce();
  });

  it("reports calculation errors without persisting", async () => {
    const deps = dependencies();
    deps.computeEmissions.mockResolvedValue({ _calculation_error: "Missing mix factor" });

    await expect(saveSimplifiedConcreteMixRow(deps)).resolves.toBe(false);

    expect(deps.setError).toHaveBeenCalledWith("Missing mix factor");
    expect(ActivityDataService.createRow).not.toHaveBeenCalled();
  });
});
