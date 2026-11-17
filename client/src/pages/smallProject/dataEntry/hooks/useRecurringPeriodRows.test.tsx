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

    it("loads electricity rows by the selected period and creates group-linked electricity placeholders", async () => {
        vi.mocked(ActivityDataService.fetchRows).mockResolvedValue([]);
        const updateElectricityRows = vi.fn();
        const stageInstance = { id: "recurring-stage", stage: "RECURRING" as const };
        const boundaries = [{
            id: "electricity-boundary",
            stage_or_activity: "Vehicle fleet",
            category: "Electricity",
            sub_category: "Electricity",
            source: "Grid Electricity",
        }];

        renderHook(() => useRecurringPeriodRows({
            activeStageInstance: stageInstance,
            periodId: "period-2035",
            projectId: "project-1",
            reportingBoundaries: boundaries,
            apiRowToUiRow: (row) => ({ ...row }),
            updateRows: vi.fn(),
            updateElectricityRows,
        }));

        await waitFor(() => expect(updateElectricityRows).toHaveBeenCalledWith([
            expect.objectContaining({
                id: "__BOUNDARY_electricity-boundary__",
                reporting_boundary_id: "electricity-boundary",
                stage_or_activity: "Vehicle fleet",
                emission_source: "Grid Electricity",
                emissions_subcategory: "Electricity",
                unit_display: "MWh",
            }),
        ]));
        expect(ActivityDataService.fetchRows).toHaveBeenCalledWith(
            "recurring-stage", "electricity", undefined, "period-2035",
        );
        expect(LookupsService.fetchBgmCategories).not.toHaveBeenCalled();
    });
});
