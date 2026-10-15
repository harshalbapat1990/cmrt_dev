import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ActivityDataService from "@/services/ActivityData.service";
import LookupsService from "@/services/Lookups.service";
import { useRecurringPeriodRows } from "./useRecurringPeriodRows";

vi.mock("@/services/ActivityData.service", () => ({
    default: { fetchRows: vi.fn() },
}));
vi.mock("@/services/Lookups.service", () => ({
    default: {
        fetchBgmCategories: vi.fn(),
        fetchBgmSubcategories: vi.fn(),
        fetchBgmSources: vi.fn(),
    },
}));

describe("useRecurringPeriodRows", () => {
    beforeEach(() => vi.clearAllMocks());

    it("loads period rows and fills in uncovered reporting boundaries", async () => {
        vi.mocked(ActivityDataService.fetchRows).mockResolvedValue([]);
        vi.mocked(LookupsService.fetchBgmCategories).mockResolvedValue([{ id: "category-id", name: "Transport" }]);
        vi.mocked(LookupsService.fetchBgmSubcategories).mockResolvedValue([{ id: "subcategory-id", name: "Road" }]);
        vi.mocked(LookupsService.fetchBgmSources).mockResolvedValue([{ id: "source-id", name: "Freight" }]);
        const updateRows = vi.fn();
        const stageInstance = { id: "recurring-stage", stage: "RECURRING" as const };
        const boundaries = [{
            id: "boundary-1",
            stage_or_activity: "Recurring",
            category: "Transport",
            sub_category: "Road",
            source: "Freight",
        }];

        renderHook(() => useRecurringPeriodRows({
            activeStageInstance: stageInstance,
            periodId: "period-1",
            projectId: "project-1",
            reportingBoundaries: boundaries,
            apiRowToUiRow: (row) => ({ ...row }),
            updateRows,
        }));

        await waitFor(() => expect(updateRows).toHaveBeenLastCalledWith("recurringG3", [expect.objectContaining({
            id: "__BOUNDARY_boundary-1__",
            reporting_boundary_id: "boundary-1",
            emissions_category_id: "category-id",
            emissions_subcategory_id: "subcategory-id",
            emissions_source: "source-id",
        })]));
        expect(ActivityDataService.fetchRows).toHaveBeenCalledWith("recurring-stage", "recurringG3", undefined, "period-1");
    });
});
