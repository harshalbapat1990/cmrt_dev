import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ActivityDataService from "@/services/ActivityData.service";
import type { DataEntryRow } from "../dataEntryTypes";
import { useDataEntryRowMutations } from "./useDataEntryRowMutations";
import type { CalcConfig } from "../useEmissionsCalc";

vi.mock("@/services/ActivityData.service", () => ({
  default: { deleteRow: vi.fn(), updateRow: vi.fn() },
}));
vi.mock("../refurbishmentTableConfig", () => ({ fetchAllActiveMrFactors: vi.fn() }));

describe("useDataEntryRowMutations synchronized component deletion", () => {
  it("shows the server calculation after an inline asset edit", async () => {
    const row: DataEntryRow = { id: "asset-1", quantity: 150000000, _fromApi: true };
    const updateRows = vi.fn();
    const setRows = vi.fn();
    vi.mocked(ActivityDataService.updateRow).mockResolvedValue({
      id: "asset-1",
      emissions_tco2e: "24322.5",
    } as never);
    const config: CalcConfig = {
      grade: 1,
      requiredKeys: ["quantity"],
      triggerKeys: ["quantity"],
      buildPayload: () => ({}),
      calculate: async () => null,
      mapResultToRow: () => ({}),
    };
    const { result } = renderHook(() => useDataEntryRowMutations({
      projectId: "project-1",
      user: null,
      fugitiveList: [],
      getRows: () => [row],
      updateRows,
      setErrorForKey: vi.fn(),
      getCalcConfig: () => config,
      computeEmissionsForRow: async () => ({ total_emissions_tco2e: 68550 }),
      refreshOptionTotals: vi.fn(async () => undefined),
      recalcElectricitySiblings: async () => undefined,
      validateElectricityYear: () => null,
      validateComponentReplLife: () => null,
      handleSaveBoundaryRow: async () => undefined,
      syncComponentQtyToReplacement: async () => undefined,
      deleteTarget: null,
      setDeleteTarget: vi.fn(),
    }));

    await act(async () => result.current.onCellChange("asset", setRows)({
      id: "asset-1",
      key: "quantity",
      value: 150000000,
      item: row,
    }));

    expect(ActivityDataService.updateRow).toHaveBeenCalledOnce();
    const finalStateUpdate = setRows.mock.calls.at(-1)?.[0] as (rows: DataEntryRow[]) => DataEntryRow[];
    expect(finalStateUpdate([row])[0]).toMatchObject({
      emissions_tco2e: 24322.5,
      total_emissions_tco2e: 24322.5,
    });
  });

  it("shows the backend emissions result after saving a Grade 3 detailed-level edit", async () => {
    const row: DataEntryRow = { id: "detail-1", quantity: 2000, _fromApi: true };
    const updateRows = vi.fn();
    const setRows = vi.fn();
    const refreshOptionTotals = vi.fn(async () => undefined);
    const config: CalcConfig = {
      grade: 3,
      requiredKeys: ["quantity"],
      triggerKeys: ["quantity"],
      buildPayload: () => ({}),
      calculate: async () => null,
      mapResultToRow: () => ({}),
    };
    vi.mocked(ActivityDataService.updateRow).mockResolvedValue({
      id: "detail-1",
      emissions_tco2e: "9.230379",
    } as never);

    const { result } = renderHook(() => useDataEntryRowMutations({
      projectId: "project-1",
      user: null,
      fugitiveList: [],
      getRows: () => [row],
      updateRows,
      setErrorForKey: vi.fn(),
      getCalcConfig: () => config,
      computeEmissionsForRow: async () => ({ total_emissions_tco2e: 0 }),
      refreshOptionTotals,
      recalcElectricitySiblings: async () => undefined,
      validateElectricityYear: () => null,
      validateComponentReplLife: () => null,
      handleSaveBoundaryRow: async () => undefined,
      syncComponentQtyToReplacement: async () => undefined,
      deleteTarget: null,
      setDeleteTarget: vi.fn(),
    }));

    await act(async () => result.current.onCellChange("bcDetailedLevel", setRows)({
      id: "detail-1",
      key: "quantity",
      value: 2000,
      item: row,
    }));

    const serverStateUpdate = setRows.mock.calls.at(-1)?.[0] as (rows: DataEntryRow[]) => DataEntryRow[];
    expect(serverStateUpdate([row])[0]).toMatchObject({
      emissions_tco2e: 9.230379,
      total_emissions_tco2e: 9.230379,
    });
    expect(ActivityDataService.updateRow).toHaveBeenCalledOnce();
    expect(refreshOptionTotals).toHaveBeenCalledOnce();
  });

  it("deletes the linked replacement row before removing the component", async () => {
    const component: DataEntryRow = { id: "component-1" };
    const replacement: DataEntryRow = {
      id: "replacement-1",
      _fromApi: true,
      _syncedSourceId: "component-1",
    };
    const componentRows: DataEntryRow[] = [component];
    const replacementRows: DataEntryRow[] = [replacement];
    const updateRows = vi.fn();
    const setDeleteTarget = vi.fn();
    const setErrorForKey = vi.fn();
    const refreshOptionTotals = vi.fn(async () => undefined);
    vi.mocked(ActivityDataService.deleteRow).mockResolvedValue(undefined as never);
    const { result } = renderHook(() => useDataEntryRowMutations({
      user: null,
      fugitiveList: [],
      getRows: (key) => key === "componentRepl" ? replacementRows : componentRows,
      updateRows,
      setErrorForKey,
      getCalcConfig: () => null,
      computeEmissionsForRow: async () => null,
      refreshOptionTotals,
      recalcElectricitySiblings: async () => undefined,
      validateElectricityYear: () => null,
      validateComponentReplLife: () => null,
      handleSaveBoundaryRow: async () => undefined,
      syncComponentQtyToReplacement: async () => undefined,
      deleteTarget: { id: "component-1", tableKey: "component" },
      setDeleteTarget,
    }));

    await act(async () => result.current.doDeleteRow());

    expect(ActivityDataService.deleteRow).toHaveBeenNthCalledWith(1, "replacement-1");
    expect(ActivityDataService.deleteRow).toHaveBeenNthCalledWith(2, "component-1");
    expect(updateRows).toHaveBeenCalledWith("componentRepl", expect.any(Function));
    expect(updateRows).toHaveBeenCalledWith("component", expect.any(Function));
    expect(refreshOptionTotals).toHaveBeenCalledOnce();
    expect(setDeleteTarget).toHaveBeenCalledWith(null);
  });

  it("synchronizes an edited component quantity through the replacement update action", async () => {
    const component: DataEntryRow = { id: "component-1", quantity: 2, _fromApi: true };
    const replacement: DataEntryRow = {
      id: "replacement-1",
      quantity: 2,
      _fromApi: true,
      _syncedSourceId: "component-1",
    };
    const config: CalcConfig = {
      grade: 1,
      requiredKeys: [],
      triggerKeys: ["quantity"],
      buildPayload: () => ({}),
      calculate: async () => null,
      mapResultToRow: () => ({}),
    };
    const componentRows = [component];
    const replacementRows = [replacement];
    const updateRows = vi.fn();
    const refreshOptionTotals = vi.fn(async () => undefined);
    const computeEmissionsForRow = vi.fn(async (key: string, row: DataEntryRow) =>
      key === "componentRepl" ? { total_emissions_tco2e: Number(row.quantity) * 2 } : { total_emissions_tco2e: 6 },
    );
    vi.mocked(ActivityDataService.updateRow).mockResolvedValue(undefined as never);

    const { result } = renderHook(() => useDataEntryRowMutations({
      user: null,
      fugitiveList: [],
      getRows: (key) => key === "componentRepl" ? replacementRows : componentRows,
      updateRows,
      setErrorForKey: vi.fn(),
      getCalcConfig: () => config,
      computeEmissionsForRow,
      refreshOptionTotals,
      recalcElectricitySiblings: async () => undefined,
      validateElectricityYear: () => null,
      validateComponentReplLife: () => null,
      handleSaveBoundaryRow: async () => undefined,
      syncComponentQtyToReplacement: async () => undefined,
      deleteTarget: null,
      setDeleteTarget: vi.fn(),
    }));

    await act(async () => result.current.onRowPatch("component", vi.fn())({
      id: "component-1",
      patch: { quantity: 5 },
      item: component,
    }));

    expect(computeEmissionsForRow).toHaveBeenCalledWith("componentRepl", expect.objectContaining({ quantity: 5 }));
    expect(ActivityDataService.updateRow).toHaveBeenNthCalledWith(2, "replacement-1", expect.objectContaining({
      quantity: 5,
      emissions_tco2e: 10,
      extra_fields: expect.not.objectContaining({ _fromApi: true, id: "replacement-1" }),
    }));
    expect(updateRows).toHaveBeenCalledWith("componentRepl", expect.any(Function));
    expect(refreshOptionTotals).toHaveBeenCalledOnce();
  });

  it("keeps a row in place and leaves confirmation open when deletion fails", async () => {
    const updateRows = vi.fn();
    const setDeleteTarget = vi.fn();
    vi.mocked(ActivityDataService.deleteRow).mockRejectedValueOnce(new Error("Delete failed"));
    const { result } = renderHook(() => useDataEntryRowMutations({
      user: null,
      fugitiveList: [],
      getRows: () => [],
      updateRows,
      setErrorForKey: vi.fn(),
      getCalcConfig: () => null,
      computeEmissionsForRow: async () => null,
      refreshOptionTotals: vi.fn(async () => undefined),
      recalcElectricitySiblings: async () => undefined,
      validateElectricityYear: () => null,
      validateComponentReplLife: () => null,
      handleSaveBoundaryRow: async () => undefined,
      syncComponentQtyToReplacement: async () => undefined,
      deleteTarget: { id: "row-1", tableKey: "asset" },
      setDeleteTarget,
    }));

    await expect(result.current.doDeleteRow()).rejects.toThrow("Delete failed");
    expect(updateRows).not.toHaveBeenCalled();
    expect(setDeleteTarget).not.toHaveBeenCalledWith(null);
  });
});
