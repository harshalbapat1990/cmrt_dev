import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ActivityDataService from "@/services/ActivityData.service";
import { useCopyDataLoader } from "./useCopyDataLoader";

vi.mock("@/services/ActivityData.service", () => ({
    default: { fetchRows: vi.fn() },
}));

describe("useCopyDataLoader", () => {
    it("reloads copied Use-stage rows and closes the dialog", async () => {
        vi.mocked(ActivityDataService.fetchRows).mockImplementation(async (_stageId, tableKey) => [{
            id: `${tableKey}-row`,
            project_id: "project-1",
            project_stage_instance_id: "stage-1",
            quantity: 1,
            ui_table_key: tableKey,
        }]);
        const closeCopyDialog = vi.fn();
        const updateRows = vi.fn();
        const refreshUsers = vi.fn();
        const stageInstance = { id: "stage-1", stage: "BUSINESS_CASE" as const };
        const apiRowToUiRow = (row: { id: string }) => ({ id: row.id });
        const resolveBoundaryComponentIds = vi.fn();
        const { result } = renderHook(() => useCopyDataLoader({
            activeSubStage: "Use (B1)",
            activeStageInstance: stageInstance,
            activeOptionId: "option-1",
            projectClass: "LARGE",
            reportingBoundaries: [],
            updateRows,
            apiRowToUiRow,
            resolveBoundaryComponentIds,
            closeCopyDialog,
            refreshUsers,
        }));

        await result.current();

        expect(closeCopyDialog).toHaveBeenCalledOnce();
        expect(ActivityDataService.fetchRows).toHaveBeenCalledTimes(2);
        expect(updateRows).toHaveBeenCalledWith("useB1G2", [{ id: "useB1G2-row" }]);
        expect(updateRows).toHaveBeenCalledWith("useB1G3", [{ id: "useB1G3-row" }]);
    });
});
