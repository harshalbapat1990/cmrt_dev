import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useDesignSeedWorkflow } from "./useDesignSeedWorkflow";

describe("useDesignSeedWorkflow", () => {
  it("confirms the selected design report and seeds the construction periods", async () => {
    const seedPeriodsFromDesign = vi.fn(async () => undefined);
    const { result } = renderHook(() => useDesignSeedWorkflow());

    act(() => result.current.requestReportChange(3));
    expect(result.current.confirmOpen).toBe(true);
    expect(result.current.pendingDesignReportNum).toBe(3);

    await act(async () => result.current.confirmReportChange(seedPeriodsFromDesign, ["period-1", "period-2"]));
    expect(result.current.designReportNum).toBe(3);
    expect(result.current.confirmOpen).toBe(false);
    expect(result.current.pendingDesignReportNum).toBeNull();
    expect(result.current.isSeeding).toBe(false);
    expect(seedPeriodsFromDesign).toHaveBeenCalledWith(["period-1", "period-2"]);
  });

  it("clears the pending report when canceled", () => {
    const { result } = renderHook(() => useDesignSeedWorkflow());
    act(() => result.current.requestReportChange(2));
    act(() => result.current.cancelReportChange());
    expect(result.current.confirmOpen).toBe(false);
    expect(result.current.pendingDesignReportNum).toBeNull();
  });
});
