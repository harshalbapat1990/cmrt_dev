import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import type { ProjectOption } from "@/services/ProjectOptions.service";
import { ConstructionPeriodsService } from "@/services/ConstructionPeriods.service";
import { useExecSummary } from "./useExecSummary";

vi.mock("@/services/ConstructionPeriods.service", () => ({
    ConstructionPeriodsService: { saveExecSummary: vi.fn() },
}));
vi.mock("@/services/ProjectOptions.service", () => ({
    default: { saveExecSummary: vi.fn() },
}));

const period = {
    id: "period-1",
    exec_summary: "Recurring period summary",
    exec_summary_author: "Demo User",
    exec_summary_date: "2026-10-28T11:15:27.286000",
} as ConstructionPeriod;

describe("useExecSummary", () => {
    it("loads and saves recurring summaries against the selected reporting period", async () => {
        const updated = { ...period, exec_summary: "Updated recurring summary" };
        vi.mocked(ConstructionPeriodsService.saveExecSummary).mockResolvedValue(updated);
        const setConstructionPeriods = vi.fn();
        const setProjectOptions = vi.fn();

        const { result } = renderHook(() => useExecSummary({
            activeStage: "Recurring",
            activeOption: null,
            activePeriod: period,
            activeOptionId: "option-1",
            user: null,
            success: vi.fn(),
            setConstructionPeriods,
            setProjectOptions,
        }));

        expect(result.current.execSummary).toBe("Recurring period summary");
        act(() => result.current.setExecSummary("Updated recurring summary"));
        await act(async () => result.current.saveExecSummary());

        expect(ConstructionPeriodsService.saveExecSummary).toHaveBeenCalledWith(
            "period-1",
            "Updated recurring summary",
            "",
            expect.any(String),
        );
        expect(setConstructionPeriods).toHaveBeenCalledWith(expect.any(Function));
        expect(setProjectOptions).not.toHaveBeenCalled();
    });
});
