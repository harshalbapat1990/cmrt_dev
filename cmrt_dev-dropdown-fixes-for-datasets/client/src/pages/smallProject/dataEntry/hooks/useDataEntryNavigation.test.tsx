import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { NavigateFunction } from "react-router-dom";
import type { StageNavigationItem } from "../stageNavigationOptions";
import { useDataEntryNavigation } from "./useDataEntryNavigation";

const stages: StageNavigationItem[] = [
    { label: "Design (2 of 2)", value: "Design__2", stageLabel: "Design", reportNumber: 2, disabled: false },
    { label: "Unavailable", value: "Unavailable__1", stageLabel: "Business case", reportNumber: 1, disabled: true },
    { label: "Results dashboard", value: "RESULTS_DASHBOARD", stageLabel: "RESULTS_DASHBOARD", reportNumber: 1, disabled: false },
];

function createParams() {
    return {
        projectId: "project-1",
        projectData: null,
        projectClass: "SMALL" as const,
        activeSubStage: "Construction",
        subStages: ["Construction", "Replacement"],
        stages,
        mitigationsEnabled: true,
        completenessEnabled: true,
        navigate: vi.fn() as unknown as NavigateFunction,
        setActiveStage: vi.fn(),
        setActiveReportNumber: vi.fn(),
        setActiveSubStage: vi.fn(),
        setShowMitigations: vi.fn(),
        setShowCompleteness: vi.fn(),
        setShowAuditPanel: vi.fn(),
    };
}

describe("useDataEntryNavigation", () => {
    it("selects an enabled stage and resets its transient panels", () => {
        const params = createParams();
        const { result } = renderHook(() => useDataEntryNavigation(params));

        act(() => result.current.selectStage("Design__2"));

        expect(params.setActiveStage).toHaveBeenCalledWith("Design");
        expect(params.setActiveReportNumber).toHaveBeenCalledWith(2);
        expect(params.setActiveSubStage).toHaveBeenCalledWith("Construction");
        expect(params.setShowMitigations).toHaveBeenCalledWith(false);
        expect(params.setShowCompleteness).toHaveBeenCalledWith(false);
        expect(params.setShowAuditPanel).toHaveBeenCalledWith(false);

        act(() => result.current.selectStage("Unavailable__1"));
        expect(params.setActiveStage).toHaveBeenCalledTimes(1);
    });

    it("navigates to Results Dashboard with project context and supports substage movement", () => {
        const params = createParams();
        const { result } = renderHook(() => useDataEntryNavigation(params));

        act(() => result.current.selectStage("RESULTS_DASHBOARD"));
        expect(params.navigate).toHaveBeenCalledWith(
            "/resultsDashboard?projectId=project-1",
            { state: { projectData: null } },
        );

        act(() => result.current.guardedAction("next"));
        expect(params.setActiveSubStage).toHaveBeenCalledWith("Replacement");

        const previousParams = { ...createParams(), activeSubStage: "Replacement" };
        const previous = renderHook(() => useDataEntryNavigation(previousParams));
        act(() => previous.result.current.goToPreviousSubStage());
        expect(previousParams.setActiveSubStage).toHaveBeenCalledWith("Construction");
    });
});
