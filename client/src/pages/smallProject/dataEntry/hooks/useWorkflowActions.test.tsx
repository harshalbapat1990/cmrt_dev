import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Dispatch, SetStateAction } from "react";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import type { ProjectOption } from "@/services/ProjectOptions.service";
import type { StageInstance, StageLabel } from "../dataEntryTypes";
import { ConstructionPeriodsService } from "@/services/ConstructionPeriods.service";
import { useWorkflowActions } from "./useWorkflowActions";

vi.mock("@/services/ConstructionPeriods.service", () => ({
    ConstructionPeriodsService: {
        reject: vi.fn().mockResolvedValue({}),
        listPeriods: vi.fn().mockResolvedValue([]),
    },
}));

vi.mock("@/services/ProjectOptions.service", () => ({
    default: { ensureOptions: vi.fn().mockResolvedValue([]) },
}));

vi.mock("@/services/ActivityData.service", () => ({ default: { seedFromDesign: vi.fn() } }));

const period: ConstructionPeriod = {
    id: "period-1",
    project_id: "project-1",
    stage_instance_id: "stage-1",
    frequency: "monthly",
    period_label: "January 2025",
    period_start_date: "2025-01-01",
    period_end_date: "2025-01-31",
    due_date: null,
    status: "in_progress",
    submitted_by: null,
    submitted_at: null,
    decision_by: null,
    decision_at: null,
    rejection_reason: null,
    reopen_requested_by: null,
    reopen_requested_at: null,
    reopen_reason: null,
    created_on: null,
    updated_on: null,
    period_emissions_tco2e: null,
    previous_period_emissions_tco2e: null,
    all_periods_emissions_tco2e: null,
};

function setter<T>(): Dispatch<SetStateAction<T>> {
    return vi.fn() as Dispatch<SetStateAction<T>>;
}

function createParams() {
    const activeStageInstance: StageInstance = { id: "stage-1", stage: "CONSTRUCTION" };
    return {
        activeStage: "Construction" as StageLabel,
        activeStageInstance,
        activeOptionId: "option-1",
        activeOption: null as ProjectOption | null,
        activePeriod: period,
        constructionPeriods: [period],
        designSeedOptionId: null,
        success: vi.fn(),
        setProjectOptions: setter<ProjectOption[]>(),
        setConstructionPeriods: setter<ConstructionPeriod[]>(),
        setSelectedConstructionMonth: setter<string | null>(),
    };
}

describe("useWorkflowActions period confirmations", () => {
    it("does not submit a reason-required action without a nonblank reason", async () => {
        vi.mocked(ConstructionPeriodsService.reject).mockClear();
        const { result } = renderHook(() => useWorkflowActions(createParams()));

        act(() => result.current.setPeriodWorkflowOpen("reject"));
        await act(async () => result.current.handlePeriodWorkflowConfirm("  "));

        expect(ConstructionPeriodsService.reject).not.toHaveBeenCalled();
        expect(result.current.periodWorkflowOpen).toBe("reject");
    });

    it("trims and submits the required reason", async () => {
        vi.mocked(ConstructionPeriodsService.reject).mockClear();
        const { result } = renderHook(() => useWorkflowActions(createParams()));

        act(() => result.current.setPeriodWorkflowOpen("reject"));
        await act(async () => result.current.handlePeriodWorkflowConfirm("  Needs correction  "));

        expect(ConstructionPeriodsService.reject).toHaveBeenCalledWith("period-1", "Needs correction");
    });
});
