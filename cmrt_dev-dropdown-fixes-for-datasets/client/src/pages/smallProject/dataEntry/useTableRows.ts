import { useState, useCallback } from "react";
import type { UploadKey } from "./stageConstants";
import type { DataEntryRow, TableRowMap } from "./dataEntryTypes";

export function emptyRowMap(): TableRowMap {
    return {
        asset: [],
        component: [],
        componentRepl: [],
        refurbishment: [],
        replDetailed: [],
        opEnergy: [],
        opEnergyDetailed: [],
        opEnergyElectricity: [],
        constructionG2: [],
        constructionG3: [],
        bcDetailedLevel: [],
        electricity: [],
        useB1G2: [],
        useB1G3: [],
        concreteRegSimplified: [],
        concreteRegDetailed: [],
        recurringG3: [],
    };
}

export function keepTableRows(
    rows: TableRowMap,
    keysToKeep: readonly UploadKey[],
): TableRowMap {
    const keptRows = emptyRowMap();
    for (const key of keysToKeep) keptRows[key] = rows[key];
    return keptRows;
}

export function useTableRows() {
    const [tableRows, setTableRows] = useState<TableRowMap>(emptyRowMap);

    const getRows = (key: UploadKey): DataEntryRow[] => tableRows[key];

    const updateRows = useCallback(
        (key: UploadKey, updater: DataEntryRow[] | ((prev: DataEntryRow[]) => DataEntryRow[])) =>
            setTableRows((prev) => ({
                ...prev,
                [key]: typeof updater === "function" ? updater(prev[key] ?? []) : updater,
            })),
        []
    );

    const [tableErrors, setTableErrors] = useState<Partial<Record<UploadKey, string | null>>>({});

    const setErrorForKey = (tableKey: UploadKey, msg: string | null) =>
        setTableErrors((prev) => ({ ...prev, [tableKey]: msg }));

    return {
        tableRows,
        setTableRows,
        getRows,
        updateRows,
        tableErrors,
        setErrorForKey,
    };
}
