import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ActivityDataService from "@/services/ActivityData.service";
import { useConstructionPeriodRows } from "./useConstructionPeriodRows";

vi.mock("@/services/ActivityData.service", () => ({
    default: { fetchRows: vi.fn() },
}));

describe("useConstructionPeriodRows", () => {
    beforeEach(() => vi.clearAllMocks());

    it("loads selected-period rows and adds missing construction boundary rows", async () => {
        vi.mocked(ActivityDataService.fetchRows).mockResolvedValue([]);
        const updateRows = vi.fn();
        const stageInstance = { id: "construction-stage", stage: "CONSTRUCTION" as const };
        const boundary = {
            id: "boundary-1",
            stage_or_activity: "Construction",
            category: "Transport",
            sub_category: "Road",
        };
        const apiRowToUiRow = (row: { id: string }) => ({ id: row.id });
        const resolveBoundaryComponentIds = vi.fn().mockResolvedValue({
            emissions_category_id: "category-id",
            emissions_subcategory_id: "subcategory-id",
            emissions_source: null,
        });

        renderHook(() => useConstructionPeriodRows({
            enabled: true,
            activeStage: "Construction",
            activeSubStage: "Construction",
            activeStageInstance: stageInstance,
            periodId: "period-1",
            projectClass: "SMALL",
            reportingBoundaries: [boundary],
            updateRows,
            apiRowToUiRow,
            resolveBoundaryComponentIds,
            recalcAndPersistRows: vi.fn(),
        }));

        await waitFor(() => expect(updateRows).toHaveBeenCalledWith("constructionG2", [expect.objectContaining({
            id: "__BOUNDARY_boundary-1__",
            emissions_category_id: "category-id",
        })]));
        expect(ActivityDataService.fetchRows).toHaveBeenCalledWith("construction-stage", "constructionG2", undefined, "period-1");
        expect(updateRows).toHaveBeenCalledWith("constructionG3", []);
    });
});
