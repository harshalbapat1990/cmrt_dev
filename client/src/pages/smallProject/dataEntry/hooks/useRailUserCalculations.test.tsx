import { act, renderHook } from "@testing-library/react";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { RailUserRow } from "../userDataMapping";
import { useRailUserCalculations } from "./useRailUserCalculations";

const { calculateRailUserRow } = vi.hoisted(() => ({ calculateRailUserRow: vi.fn() }));
vi.mock("../roadUserWorkflow", () => ({ calculateRailUserRow }));

const railRow: RailUserRow = {
  id: "rail-1",
  vehicleType: "Container Train",
  terrain: "Flat",
  freight: "25",
  dieselEmissionsIntensity: "",
  dieselEmissions: "",
  dieselEmissionsTotalRefPeriod: "",
  notes: "",
};

describe("useRailUserCalculations", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });
  afterEach(() => vi.useRealTimers());

  it("debounces calculation and persists the calculated row", async () => {
    const calculatedRow = { ...railRow, dieselEmissionsTotalRefPeriod: "42" };
    calculateRailUserRow.mockResolvedValue(calculatedRow);
    const persistRows = vi.fn(async () => undefined);
    const { result } = renderHook(() => {
      const [rows, setRows] = useState([railRow]);
      return {
        rows,
        calculations: useRailUserCalculations({ projectId: "project-1", setRows, persistRows }),
      };
    });

    act(() => result.current.calculations.scheduleCalculation(railRow, [railRow]));
    await act(async () => { vi.advanceTimersByTime(799); });
    expect(calculateRailUserRow).not.toHaveBeenCalled();

    await act(async () => { vi.advanceTimersByTime(1); });
    expect(calculateRailUserRow).toHaveBeenCalledWith("project-1", railRow);
    expect(result.current.rows[0].dieselEmissionsTotalRefPeriod).toBe("42");
    expect(persistRows).toHaveBeenCalledWith([calculatedRow]);
  });

  it("ignores an older result after a newer calculation for the same rail type starts", async () => {
    let resolveFirst!: (row: RailUserRow) => void;
    let resolveSecond!: (row: RailUserRow) => void;
    calculateRailUserRow
      .mockImplementationOnce(() => new Promise<RailUserRow>((resolve) => { resolveFirst = resolve; }))
      .mockImplementationOnce(() => new Promise<RailUserRow>((resolve) => { resolveSecond = resolve; }));
    const persistRows = vi.fn(async () => undefined);
    const { result } = renderHook(() => {
      const [rows, setRows] = useState([railRow]);
      return {
        rows,
        calculations: useRailUserCalculations({ projectId: "project-1", setRows, persistRows }),
      };
    });

    act(() => result.current.calculations.scheduleCalculation(railRow, [railRow]));
    await act(async () => { vi.advanceTimersByTime(800); });
    act(() => result.current.calculations.scheduleCalculation(railRow, [railRow]));
    await act(async () => { vi.advanceTimersByTime(800); });

    await act(async () => {
      resolveFirst({ ...railRow, dieselEmissionsTotalRefPeriod: "old" });
      await Promise.resolve();
    });
    expect(persistRows).not.toHaveBeenCalled();

    await act(async () => {
      resolveSecond({ ...railRow, dieselEmissionsTotalRefPeriod: "new" });
      await Promise.resolve();
    });
    expect(result.current.rows[0].dieselEmissionsTotalRefPeriod).toBe("new");
    expect(persistRows).toHaveBeenCalledOnce();
  });

  it("skips calculation for incomplete rail rows", async () => {
    const incomplete = { ...railRow, freight: "" };
    const persistRows = vi.fn(async () => undefined);
    const { result } = renderHook(() => useRailUserCalculations({
      projectId: "project-1",
      setRows: vi.fn(),
      persistRows,
    }));

    act(() => result.current.scheduleCalculation(incomplete, [incomplete]));
    await act(async () => { vi.advanceTimersByTime(800); });

    expect(calculateRailUserRow).not.toHaveBeenCalled();
    expect(persistRows).not.toHaveBeenCalled();
  });

  it("debounces persistence-only rail edits and saves the latest rows", async () => {
    const persistRows = vi.fn(async () => undefined);
    const updatedRows = [{ ...railRow, notes: "latest note" }];
    const { result } = renderHook(() => useRailUserCalculations({
      projectId: "project-1",
      setRows: vi.fn(),
      persistRows,
    }));

    act(() => {
      result.current.scheduleSave([railRow]);
      result.current.scheduleSave(updatedRows);
    });
    await act(async () => { vi.advanceTimersByTime(799); });
    expect(persistRows).not.toHaveBeenCalled();

    await act(async () => { vi.advanceTimersByTime(1); });
    expect(persistRows).toHaveBeenCalledOnce();
    expect(persistRows).toHaveBeenCalledWith(updatedRows);
  });

  it("does not persist when the rail calculation fails", async () => {
    const error = new Error("rail calculation failed");
    calculateRailUserRow.mockRejectedValueOnce(error);
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const persistRows = vi.fn(async () => undefined);
    const { result } = renderHook(() => {
      const [rows, setRows] = useState([railRow]);
      return {
        rows,
        calculations: useRailUserCalculations({ projectId: "project-1", setRows, persistRows }),
      };
    });

    act(() => result.current.calculations.scheduleCalculation(railRow, [railRow]));
    await act(async () => { vi.advanceTimersByTime(800); });

    expect(persistRows).not.toHaveBeenCalled();
    expect(result.current.rows).toEqual([railRow]);
    expect(errorSpy).toHaveBeenCalledWith("Failed to calculate rail emissions:", error);
    errorSpy.mockRestore();
  });
});
