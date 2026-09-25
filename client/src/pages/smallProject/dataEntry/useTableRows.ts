import { useState, useCallback } from "react";
import type { UploadKey } from "./stageConstants";

const ALL_UPLOAD_KEYS: UploadKey[] = [
    "asset", "component", "componentRepl", "refurbishment", "replDetailed",
    "opEnergy", "opEnergyDetailed", "opEnergyElectricity", "constructionG2",
    "constructionG3", "bcDetailedLevel", "electricity", "useB1G2", "useB1G3",
    "concreteRegSimplified", "concreteRegDetailed", "recurringG3",
];

function emptyRowMap(): Record<UploadKey, any[]> {
    return Object.fromEntries(ALL_UPLOAD_KEYS.map((k) => [k, []])) as unknown as Record<UploadKey, any[]>;
}

export function useTableRows() {
    const [tableRows, setTableRows] = useState<Record<UploadKey, any[]>>(emptyRowMap);

    const getRows = (key: UploadKey): any[] => tableRows[key] ?? [];

    const updateRows = useCallback(
        (key: UploadKey, updater: any[] | ((prev: any[]) => any[])) =>
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
