import type { Dispatch, SetStateAction } from "react";
import { describe, expect, it, vi } from "vitest";
import type { DataEntryRow } from "./dataEntryTypes";
import { createMitigationOnCellChange, createMitigationOnRowPatch } from "./mitigationInlineEditHandlers";

function createRowsSetter(initial: DataEntryRow[]) {
  let rows = initial;
  const setRows: Dispatch<SetStateAction<DataEntryRow[]>> = (next) => {
    rows = typeof next === "function" ? next(rows) : next;
  };
  return { setRows, rows: () => rows };
}

describe("mitigation inline edit handlers", () => {
  it("blocks replacement life values above the project life", async () => {
    const row: DataEntryRow = { id: "replacement-1", life: 20 };
    const state = createRowsSetter([row]);
    const setError = vi.fn();
    const calculate = vi.fn();
    const onCellChange = createMitigationOnCellChange({
      computeEmissionsForRow: calculate,
      getCalcConfig: () => ({ triggerKeys: ["life"], requiredKeys: [] }),
      user: null,
      fugitiveList: [],
      operationalLifeYears: 15,
      constructionStartDate: null,
      constructionEndDate: null,
      opsStartYear: null,
    });

    await onCellChange("componentRepl", state.setRows, setError)({
      id: "replacement-1",
      key: "life",
      value: 20,
      item: row,
    });

    expect(setError).toHaveBeenCalledWith("Life (years) must be less than or equal to the operational life of project (15 years).");
    expect(calculate).not.toHaveBeenCalled();
    expect(state.rows()[0].life).toBe(20);
  });

  it("applies selected fugitive equipment details without triggering calculation", async () => {
    const row: DataEntryRow = { id: "fugitive-1" };
    const state = createRowsSetter([row]);
    const calculate = vi.fn();
    const onCellChange = createMitigationOnCellChange({
      computeEmissionsForRow: calculate,
      getCalcConfig: () => null,
      user: null,
      fugitiveList: [{ id: "equipment-1", equipment_type: "Chiller", default_annual_leakage_rate: "2.5" }],
      operationalLifeYears: null,
      constructionStartDate: null,
      constructionEndDate: null,
      opsStartYear: null,
    });

    await onCellChange("useB1G2", state.setRows)({
      id: "fugitive-1",
      key: "application_type_id",
      value: "equipment-1",
      item: row,
    });

    expect(state.rows()[0]).toMatchObject({
      application_type_id: "equipment-1",
      application_type: "Chiller",
      annual_leakage_rate_percent: 2.5,
    });
    expect(calculate).not.toHaveBeenCalled();
  });

  it("reports an invalid electricity year and skips calculation", async () => {
    const row: DataEntryRow = { id: "electricity-1", year: 2025, quantity_mwh: 10 };
    const state = createRowsSetter([row]);
    const setError = vi.fn();
    const calculate = vi.fn();
    const onCellChange = createMitigationOnCellChange({
      computeEmissionsForRow: calculate,
      getCalcConfig: () => null,
      user: null,
      fugitiveList: [],
      operationalLifeYears: null,
      constructionStartDate: "2030-01-01",
      constructionEndDate: "2040-01-01",
      opsStartYear: null,
    });

    await onCellChange("electricity", state.setRows, setError)({
      id: "electricity-1",
      key: "year",
      value: 2025,
      item: row,
    });

    expect(setError).toHaveBeenCalledWith("Year must be between 2030 and 2040 for the construction period.");
    expect(calculate).not.toHaveBeenCalled();
  });

  it("applies a calculated patch after a trigger field changes", async () => {
    const row: DataEntryRow = { id: "component-1", quantity: 2 };
    const state = createRowsSetter([row]);
    const calculate = vi.fn().mockResolvedValue({ total_emissions_tco2e: 12 });
    const onRowPatch = createMitigationOnRowPatch({
      computeEmissionsForRow: calculate,
      getCalcConfig: () => ({ triggerKeys: ["quantity"], requiredKeys: ["quantity"] }),
      user: null,
      fugitiveList: [],
      operationalLifeYears: null,
      constructionStartDate: null,
      constructionEndDate: null,
      opsStartYear: null,
    });

    await onRowPatch("component", state.setRows)({
      id: "component-1",
      patch: { quantity: 4 },
      item: row,
    });

    expect(calculate).toHaveBeenCalledWith("component", { id: "component-1", quantity: 4 });
    expect(state.rows()[0]).toMatchObject({ quantity: 4, total_emissions_tco2e: 12 });
  });
});
