import { renderHook, waitFor } from "@testing-library/react";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ConstructionPeriodsService } from "@/services/ConstructionPeriods.service";
import { useConstructionPeriods } from "./useConstructionPeriods";

vi.mock("@/services/ConstructionPeriods.service", () => ({
    ConstructionPeriodsService: { listPeriods: vi.fn() },
}));

describe("useConstructionPeriods", () => {
    beforeEach(() => vi.clearAllMocks());

    it("loads periods for construction and selects the first period that is not approved", async () => {
        vi.mocked(ConstructionPeriodsService.listPeriods).mockResolvedValue([
            { id: "period-approved", status: "approved" },
            { id: "period-open", status: "draft" },
        ]);
        const setPeriods = vi.fn();
        const stageInstance = { id: "stage-1", stage: "CONSTRUCTION" as const };

        const { result } = renderHook(() => {
            const [periodId, setPeriodId] = useState<string | null>(null);
            useConstructionPeriods({
                enabled: true,
                activeStage: "Construction",
                activeStageInstance: stageInstance,
                setPeriods,
                setSelectedPeriodId: setPeriodId,
            });
            return periodId;
        });

        await waitFor(() => expect(setPeriods).toHaveBeenCalledWith([
            { id: "period-approved", status: "approved" },
            { id: "period-open", status: "draft" },
        ]));
        await waitFor(() => expect(result.current).toBe("period-open"));
    });

    it("does not fetch periods for other stages", async () => {
        vi.mocked(ConstructionPeriodsService.listPeriods).mockResolvedValue([
            { id: "period-open", status: "draft" },
        ]);
        const setPeriods = vi.fn();
        const stageInstance = { id: "stage-1", stage: "BUSINESS_CASE" as const };
        renderHook(() => {
            const [, setPeriodId] = useState<string | null>(null);
            useConstructionPeriods({
                enabled: false,
                activeStage: "Business case",
                activeStageInstance: stageInstance,
                setPeriods,
                setSelectedPeriodId: setPeriodId,
            });
        });

        expect(ConstructionPeriodsService.listPeriods).not.toHaveBeenCalled();
        expect(setPeriods).not.toHaveBeenCalled();
    });
});
