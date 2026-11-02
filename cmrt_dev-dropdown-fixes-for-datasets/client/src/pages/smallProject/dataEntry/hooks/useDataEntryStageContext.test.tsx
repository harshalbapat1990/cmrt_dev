import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useDataEntryStageContext } from "./useDataEntryStageContext";

const stageInstances = [
    { id: "business", stage: "BUSINESS_CASE" as const, sequence: 1, num_reports_required: 2 },
    { id: "design", stage: "DESIGN" as const, sequence: 2, num_reports_required: 1 },
];
const projectOptions = [
    { id: "bc-r1", stage_instance_id: "business", report_number: 1, label: "Report 1", is_default: true },
    { id: "bc-r2-default", stage_instance_id: "business", report_number: 2, label: "Report 2", is_default: true },
    { id: "bc-r2-alt", stage_instance_id: "business", report_number: 2, label: "Alternative", is_default: false },
    { id: "design-r1", stage_instance_id: "design", report_number: 1, label: "Design", is_default: true },
].map((option) => ({
    project_id: "project-1",
    option_number: 1,
    approval_status: "draft",
    ...option,
}));

function renderContext(selectedOptionByStage: Record<string, string> = { business: "bc-r2-alt" }) {
    return renderHook(() => useDataEntryStageContext({
        activeStage: "Business case",
        activeReportNumber: 2,
        stageInstances,
        stageAccess: [{
            stage_instance_id: "business",
            stage: "BUSINESS_CASE",
            stage_label: "Business case",
            sequence: 1,
            access: "EDIT",
        }],
        projectOptions,
        projectClass: "SMALL",
        selectedOptionByStage,
        constructionPeriods: [],
        selectedConstructionMonth: null,
        designReportNum: 1,
        reportingBoundaries: [],
        recurringRows: [],
    }));
}

describe("useDataEntryStageContext", () => {
    it("selects the active report option and exposes report navigation", () => {
        const { result } = renderContext();

        expect(result.current.activeStageInstance?.id).toBe("business");
        expect(result.current.activeStageAccess).toBe("EDIT");
        expect(result.current.activeOptionId).toBe("bc-r2-alt");
        expect(result.current.currentReportSubOptions.map((option) => option.id)).toEqual([
            "bc-r2-default",
            "bc-r2-alt",
        ]);
        expect(result.current.enrichedStages.map((stage) => stage.value)).toEqual([
            "Business case__1",
            "Business case__2",
            "Design__1",
            "RESULTS_DASHBOARD",
        ]);
    });

    it("falls back to the default when the saved option override is no longer in this report", () => {
        const { result } = renderContext({ business: "deleted-option" });

        expect(result.current.activeOptionId).toBe("bc-r2-default");
    });
});
