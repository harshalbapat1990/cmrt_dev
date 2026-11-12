import { renderHook, waitFor } from "@testing-library/react";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ConstructionPeriodsService } from "@/services/ConstructionPeriods.service";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
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
        ] as ConstructionPeriod[]);
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

        await waitFor(() => expect(setPeriods).toHaveBeenCalled());
        await waitFor(() => expect(result.current).toBe("period-open"));
    });

    it("does not fetch periods for other stages", async () => {
        const setPeriods = vi.fn();
        renderHook(() => {
            const [, setPeriodId] = useState<string | null>(null);
            useConstructionPeriods({
                enabled: false,
                activeStage: "Business case",
                activeStageInstance: { id: "stage-1", stage: "BUSINESS_CASE" },
                setPeriods,
                setSelectedPeriodId: setPeriodId,
            });
        });
        expect(ConstructionPeriodsService.listPeriods).not.toHaveBeenCalled();
        expect(setPeriods).not.toHaveBeenCalled();
    });

    it("preserves a periodId deep link after periods load", async () => {
        vi.mocked(ConstructionPeriodsService.listPeriods).mockResolvedValue([
            { id: "period-1", status: "approved" },
            { id: "period-2", status: "approved" },
        ] as ConstructionPeriod[]);
        const setPeriods = vi.fn();
        const { result } = renderHook(() => {
            const [periodId, setPeriodId] = useState<string | null>("period-2");
            useConstructionPeriods({
                enabled: true,
                activeStage: "Recurring",
                activeStageInstance: { id: "recurring-stage", stage: "RECURRING" },
                setPeriods,
                setSelectedPeriodId: setPeriodId,
            });
            return periodId;
        });
        await waitFor(() => expect(setPeriods).toHaveBeenCalled());
        expect(result.current).toBe("period-2");
    });
});
