import { act, renderHook } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import type { ActivityDataOut } from "@/services/ActivityData.service";
import type { DataEntryRow, TableRowMap } from "../dataEntryTypes";
import type { UploadKey } from "../stageConstants";
import { useRowOperations } from "./useRowOperations";

function createParams() {
    return {
        activeStageInstance: null,
        projectId: "project-1",
        activeOptionId: null,
        activePeriod: null,
        constructionStartDate: "2020-03-15",
        constructionEndDate: "2025-10-31",
        opsStartYear: 2022,
        operationalLifeYears: 10,
        user: null,
        fugitiveList: [],
        tableRows: {} as TableRowMap,
        getRows: () => [] as DataEntryRow[],
        updateRows: vi.fn(),
        setErrorForKey: vi.fn(),
        resolveMetricId: async (_row: DataEntryRow, _key: UploadKey) => null,
        apiRowToUiRow: (_row: ActivityDataOut) => ({} as DataEntryRow),
        computeEmissionsForRow: async (_key: UploadKey, _row: DataEntryRow) => null,
        getCalcConfig: (_key: UploadKey) => null,
        refreshOptionTotals: async () => undefined,
        recalcElectricitySiblings: async () => undefined,
    };
}

describe("useRowOperations validation", () => {
    it("validates electricity years against their stage-specific year windows", () => {
        const { result } = renderHook(() => useRowOperations(createParams()));

        expect(result.current.validateElectricityYear("electricity", { year: 2019 })).toContain("between 2020 and 2025");
        expect(result.current.validateElectricityYear("electricity", { year: 2024 })).toBeNull();
        expect(result.current.validateElectricityYear("opEnergyElectricity", { year: 2032 })).toBeNull();
        expect(result.current.validateElectricityYear("component", { year: 1900 })).toBeNull();
    });

    it("rejects replacement life outside the project operational life", () => {
        const { result } = renderHook(() => useRowOperations(createParams()));

        expect(result.current.validateComponentReplLife("componentRepl", { life: 0 })).toContain("positive number");
        expect(result.current.validateComponentReplLife("componentRepl", { life: 11 })).toContain("operational life");
        expect(result.current.validateComponentReplLife("componentRepl", { life: 10 })).toBeNull();
        expect(result.current.validateComponentReplLife("component", { life: 20 })).toBeNull();
    });

    it("updates local row data for a non-calculating edit", async () => {
        const params = createParams();
        const initialRow: DataEntryRow = { id: "row-1", quantity: 2, _fromApi: false };
        const { result } = renderHook(() => {
            const [rows, setRows] = useState([initialRow]);
            return { rows, setRows, operations: useRowOperations(params) };
        });

        await act(async () => {
            await result.current.operations.onCellChange("asset", result.current.setRows)({
                id: "row-1",
                key: "quantity",
                value: 4,
                item: initialRow,
            });
        });

        expect(result.current.rows[0].quantity).toBe(4);
    });
});
