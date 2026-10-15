import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ProjectOption } from "@/services/ProjectOptions.service";
import type { ConstructionPeriod, ConstructionPeriodStatus } from "@/services/ConstructionPeriods.service";
import type { StageCode, StageInstance, StageLabel } from "../dataEntryTypes";
import { useDataEntryWorkflowViewState } from "./useDataEntryWorkflowViewState";

const businessInstance: StageInstance = { id: "business", stage: "BUSINESS_CASE" };
const constructionInstance: StageInstance = { id: "construction", stage: "CONSTRUCTION" };
const draftOption: ProjectOption = {
    id: "option-1",
    project_id: "project-1",
    stage_instance_id: "business",
    report_number: 1,
    option_number: 1,
    label: "Option 1",
    is_default: true,
    approval_status: "draft",
};
const makePeriod = (status: ConstructionPeriodStatus): ConstructionPeriod => ({
    id: "period-1",
    project_id: "project-1",
    stage_instance_id: "construction",
    frequency: "Monthly",
    period_label: "January 2026",
    period_start_date: "2026-01-01",
    period_end_date: "2026-01-31",
    due_date: null,
    status,
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
});

function renderViewState(overrides: Partial<Parameters<typeof useDataEntryWorkflowViewState>[0]> = {}) {
    const base: Parameters<typeof useDataEntryWorkflowViewState>[0] = {
        activeStage: "Business case" as StageLabel,
        activeSubStage: "Construction",
        projectClass: "SMALL",
        jurisdiction: "Australia",
        activeStageAccess: "EDIT",
        activeStageInstance: businessInstance,
        activeOption: draftOption,
        activePeriod: null,
        currentReportOptionCount: 1,
        lockedStages: new Set<StageCode>(),
        projectClosed: false,
        canEditActiveStage: true,
        isProjAdmin: false,
        isProjEditor: true,
        showCompleteness: false,
        showMitigations: false,
        subStages: ["Construction", "Replacement"],
    };
    return renderHook(() => useDataEntryWorkflowViewState({ ...base, ...overrides }));
}

describe("useDataEntryWorkflowViewState", () => {
    it("keeps Business Case read-only until its options are available", () => {
        const { result } = renderViewState({ currentReportOptionCount: 0 });

        expect(result.current.isOptionsReadyForStage).toBe(false);
        expect(result.current.isReadOnly).toBe(true);
        expect(result.current.shouldShowSubmit).toBe(false);
    });

    it("uses the active construction period status for read-only and submission state", () => {
        const { result, rerender } = renderHook(
            ({ periodStatus }: { periodStatus: ConstructionPeriodStatus | null }) => useDataEntryWorkflowViewState({
                activeStage: "Construction",
                activeSubStage: "Construction",
                projectClass: "SMALL",
                jurisdiction: "Australia",
                activeStageAccess: "EDIT",
                activeStageInstance: constructionInstance,
                activeOption: draftOption,
                activePeriod: periodStatus ? makePeriod(periodStatus) : null,
                currentReportOptionCount: 0,
                lockedStages: new Set<StageCode>(),
                projectClosed: false,
                canEditActiveStage: true,
                isProjAdmin: false,
                isProjEditor: true,
                showCompleteness: true,
                showMitigations: false,
                subStages: ["Construction"],
            }),
            { initialProps: { periodStatus: "in_progress" as ConstructionPeriodStatus | null } },
        );

        expect(result.current.shouldShowSubmit).toBe(true);
        expect(result.current.isReadOnly).toBe(false);

        rerender({ periodStatus: "awaiting_approval" });
        expect(result.current.isSubmitted).toBe(true);
        expect(result.current.statusBasedReadOnly).toBe(true);
        expect(result.current.isReadOnly).toBe(true);
    });
});
