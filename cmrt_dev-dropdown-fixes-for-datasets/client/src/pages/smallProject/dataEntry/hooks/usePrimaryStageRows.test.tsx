import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ActivityDataService from "@/services/ActivityData.service";
import { usePrimaryStageRows } from "./usePrimaryStageRows";

vi.mock("@/services/ActivityData.service", () => ({
    default: { fetchRows: vi.fn() },
}));
vi.mock("../refurbishmentTableConfig", () => ({ fetchAllActiveMrFactors: vi.fn() }));

describe("usePrimaryStageRows", () => {
    beforeEach(() => vi.clearAllMocks());

    it("does not request table rows until project bootstrap is ready", () => {
        renderHook(() => usePrimaryStageRows({
            enabled: false,
            activeStage: "Business case",
            activeSubStage: "Construction",
            activeStageInstance: { id: "business-stage", stage: "BUSINESS_CASE" },
            activeOptionId: "option-1",
            projectClass: "SMALL",
            reportingBoundaries: [],
            updateRows: vi.fn(),
            setTableRows: vi.fn(),
            apiRowToUiRow: (row: { id: string }) => ({ id: row.id }),
            resolveBoundaryComponentIds: vi.fn(),
            recalcAndPersistRows: vi.fn(),
        }));

        expect(ActivityDataService.fetchRows).not.toHaveBeenCalled();
    });

    it("loads Business Case construction tables for the selected option", async () => {
        vi.mocked(ActivityDataService.fetchRows).mockImplementation(async (_stageId, tableKey) => [{
            id: `${tableKey}-row`,
            project_id: "project-1",
            project_stage_instance_id: "business-stage",
            quantity: 1,
            ui_table_key: tableKey,
            emissions_tco2e: "1",
        }]);
        const updateRows = vi.fn();
        const setTableRows = vi.fn();
        const stageInstance = { id: "business-stage", stage: "BUSINESS_CASE" as const };
        const apiRowToUiRow = (row: { id: string }) => ({ id: row.id, emissions_tco2e: 1 });
        const resolveBoundaryComponentIds = vi.fn();
        const recalcAndPersistRows = vi.fn();

        renderHook(() => usePrimaryStageRows({
            enabled: true,
            activeStage: "Business case",
            activeSubStage: "Construction",
            activeStageInstance: stageInstance,
            activeOptionId: "option-1",
            projectClass: "SMALL",
            reportingBoundaries: [],
            updateRows,
            setTableRows,
            apiRowToUiRow,
            resolveBoundaryComponentIds,
            recalcAndPersistRows,
        }));

        await waitFor(() => expect(updateRows).toHaveBeenCalledWith("component", [
            { id: "component-row", emissions_tco2e: 1 },
        ]));
        expect(ActivityDataService.fetchRows).toHaveBeenCalledTimes(2);
        expect(ActivityDataService.fetchRows).toHaveBeenCalledWith("business-stage", "asset", "option-1");
        expect(ActivityDataService.fetchRows).not.toHaveBeenCalledWith("business-stage", "componentRepl", "option-1");
        expect(setTableRows).toHaveBeenCalled();
        expect(recalcAndPersistRows).not.toHaveBeenCalled();
    });
});
