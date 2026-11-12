import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Dispatch, SetStateAction } from "react";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import type { ProjectOption } from "@/services/ProjectOptions.service";
import type { StageInstance, StageLabel } from "../dataEntryTypes";
import { ConstructionPeriodsService } from "@/services/ConstructionPeriods.service";
import ProjectOptionsService from "@/services/ProjectOptions.service";
import { useWorkflowActions } from "./useWorkflowActions";

vi.mock("@/services/ConstructionPeriods.service", () => ({
    ConstructionPeriodsService: {
        reject: vi.fn().mockResolvedValue({}),
        requestReopen: vi.fn().mockResolvedValue({}),
        approveReopen: vi.fn().mockResolvedValue({}),
        rejectReopen: vi.fn().mockResolvedValue({}),
        listPeriods: vi.fn().mockResolvedValue([]),
    },
}));

vi.mock("@/services/ProjectOptions.service", () => ({
    default: {
        ensureOptions: vi.fn().mockResolvedValue([]),
        requestReopen: vi.fn().mockResolvedValue([]),
        approveReopen: vi.fn(),
        rejectReopen: vi.fn(),
    },
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
    beforeEach(() => vi.clearAllMocks());

    it("routes admin approval of a period reopen request through the period API", async () => {
        const params = createParams();
        params.activePeriod = { ...period, status: "reopen_requested" };
        const { result } = renderHook(() => useWorkflowActions(params));
        act(() => result.current.setAdminDecisionOpen("approveReopen"));

        await act(async () => result.current.triggerAdminDecision());

        expect(ConstructionPeriodsService.approveReopen).toHaveBeenCalledWith("period-1", undefined);
        expect(ProjectOptionsService.approveReopen).not.toHaveBeenCalled();
        expect(ConstructionPeriodsService.listPeriods).toHaveBeenCalledWith("stage-1");
        expect(result.current.adminDecisionOpen).toBeNull();
    });

    it("routes admin rejection of a period reopen request through the period API", async () => {
        const params = createParams();
        params.activePeriod = { ...period, status: "reopen_requested" };
        const { result } = renderHook(() => useWorkflowActions(params));
        act(() => {
            result.current.setDecisionComments("Not enough detail");
            result.current.setAdminDecisionOpen("denyReopen");
        });

        await act(async () => result.current.triggerAdminDecision());

        expect(ConstructionPeriodsService.rejectReopen).toHaveBeenCalledWith("period-1", "Not enough detail");
        expect(ProjectOptionsService.rejectReopen).not.toHaveBeenCalled();
        expect(ConstructionPeriodsService.listPeriods).toHaveBeenCalledWith("stage-1");
    });

    it("requests a period reopen and refreshes the period list on success", async () => {
        const params = createParams();
        const { result } = renderHook(() => useWorkflowActions(params));
        act(() => result.current.setPeriodWorkflowOpen("requestReopen"));

        await act(async () => result.current.handlePeriodWorkflowConfirm("  Needs correction  "));

        expect(ConstructionPeriodsService.requestReopen).toHaveBeenCalledWith("period-1", "Needs correction");
        expect(ConstructionPeriodsService.listPeriods).toHaveBeenCalledWith("stage-1");
        expect(params.success).toHaveBeenCalledWith("Reopen request sent to admin");
        expect(result.current.periodWorkflowOpen).toBeNull();
    });

    it("keeps the Business Case and Design reopen flow on the project-option API", async () => {
        const params = createParams();
        params.activePeriod = null;
        const { result } = renderHook(() => useWorkflowActions(params));
        act(() => result.current.setReopenModalOpen(true));

        await act(async () => result.current.submitReopenRequest());

        expect(ProjectOptionsService.requestReopen).toHaveBeenCalledWith("option-1", "");
        expect(ConstructionPeriodsService.requestReopen).not.toHaveBeenCalled();
        expect(result.current.reopenModalOpen).toBe(false);
        expect(params.success).toHaveBeenCalledWith("Reopen request sent to admin");
    });

    it("retains the legacy reopen modal and exposes an API failure for retry", async () => {
        vi.mocked(ProjectOptionsService.requestReopen).mockRejectedValueOnce({
            response: { data: { detail: "The report is no longer approved" } },
        });
        const params = createParams();
        params.activePeriod = null;
        const { result } = renderHook(() => useWorkflowActions(params));
        act(() => {
            result.current.setReopenJustification("Please correct the report");
            result.current.setReopenModalOpen(true);
        });

        await act(async () => result.current.submitReopenRequest());

        expect(result.current.reopenModalOpen).toBe(true);
        expect(result.current.reopenJustification).toBe("Please correct the report");
        expect(result.current.reopenRequestError).toBe("The report is no longer approved");
    });

    it("refreshes recurring period summaries together with project option totals", async () => {
        const refreshedPeriod = { ...period, period_emissions_tco2e: 42, all_periods_emissions_tco2e: 84 };
        vi.mocked(ConstructionPeriodsService.listPeriods).mockResolvedValueOnce([refreshedPeriod]);
        const params = createParams();
        params.activeStage = "Recurring";
        params.activeStageInstance = { id: "recurring-stage", stage: "RECURRING" };
        const { result } = renderHook(() => useWorkflowActions(params));

        await act(async () => result.current.refreshOptionTotals());

        expect(ProjectOptionsService.ensureOptions).toHaveBeenCalledWith("recurring-stage");
        expect(ConstructionPeriodsService.listPeriods).toHaveBeenCalledWith("recurring-stage");
        expect(params.setConstructionPeriods).toHaveBeenCalledWith([refreshedPeriod]);
    });

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
