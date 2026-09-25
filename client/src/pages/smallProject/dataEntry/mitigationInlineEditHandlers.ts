import type React from "react";
import { fetchAllActiveMrFactors } from "./refurbishmentTableConfig";
import { type UploadKey, isElectricityTable } from "./stageConstants";
import { hasAllRequired, isValidEmission } from "./dataEntryValidation";

type CalcConfig = {
    triggerKeys: string[];
    requiredKeys: string[];
};

export type MitigationInlineCellChangeFactory = (
    tableKey: string,
    setRows: React.Dispatch<React.SetStateAction<any[]>>,
    setTableError?: (msg: string | null) => void,
) => (args: { id: any; key: any; value: any; item: any }) => Promise<void>;

export type MitigationInlineRowPatchFactory = (
    tableKey: string,
    setRows: React.Dispatch<React.SetStateAction<any[]>>,
    setTableError?: (msg: string | null) => void,
) => (args: { id: any; patch: any; item: any }) => Promise<void>;

export type MitigationInlineEditDeps = {
    computeEmissionsForRow: (tableKey: UploadKey, row: any) => Promise<Partial<any> | null>;
    getCalcConfig: (tableKey: UploadKey) => CalcConfig | null;
    user: any;
    fugitiveList: any[];
    operationalLifeYears: number | null;
    constructionStartDate: string | null;
    constructionEndDate: string | null;
    opsStartYear: number | null;
};

const getYearFromValue = (value: any): number | null => {
    if (value == null || value === "") return null;
    if (typeof value === "number") return Number.isFinite(value) ? value : null;
    const str = String(value).trim();
    if (/^\d{4}$/.test(str)) return Number(str);
    const parsed = new Date(str);
    if (!Number.isNaN(parsed.getTime())) return parsed.getFullYear();
    return null;
};

const getElectricityYearWindow = (
    tableKey: UploadKey,
     deps: MitigationElectricityYearDeps,
): { start: number | null; end: number | null; label: string } => {
    if (tableKey === "electricity") {
        return {
            start: getYearFromValue(deps.constructionStartDate),
            end: getYearFromValue(deps.constructionEndDate),
            label: "construction period",
        };
    }
    if (tableKey === "opEnergyElectricity") {
        const start = getYearFromValue(deps.opsStartYear);
        const end =
            start && deps.operationalLifeYears
                ? start + Number(deps.operationalLifeYears)
                : null;
        return { start, end, label: "operational period" };
    }
    return { start: null, end: null, label: "" };
};

export type MitigationElectricityYearDeps = Pick<
    MitigationInlineEditDeps,
    "constructionStartDate" | "constructionEndDate" | "opsStartYear" | "operationalLifeYears"
>;

export function validateMitigationElectricityYear(
    tableKey: UploadKey,
    row: any,
    deps: MitigationElectricityYearDeps,
): string | null {
    if (!isElectricityTable(tableKey)) return null;
    const year = Number(row?.year);
    if (!Number.isFinite(year)) return null;
    const { start, end, label } = getElectricityYearWindow(tableKey, deps);
    if (!start || !end) {
        return tableKey === "electricity"
            ? "Construction start and end year are required for electricity calculations."
            : "Operations start year and operational life are required for electricity calculations.";
    }
    if (year < start || year > end) {
        return `Year must be between ${start} and ${end} for the ${label}.`;
    }
    return null;
}

const validateElectricityYear = (
    tableKey: UploadKey,
    row: any,
    deps: MitigationInlineEditDeps,
): string | null => validateMitigationElectricityYear(tableKey, row, deps);

const validateComponentReplLife = (
    tableKey: UploadKey,
    row: any,
    deps: MitigationInlineEditDeps,
): string | null => {
    if (tableKey !== "componentRepl") return null;
    const rawLife = row?.life;
    if (rawLife === undefined || rawLife === null || rawLife === "") return null;
    const life = Number(rawLife);
    if (!Number.isFinite(life) || life <= 0) {
        return "Life (years) must be a valid positive number.";
    }
    const opLife = Number(deps.operationalLifeYears);
    if (Number.isFinite(opLife) && life >= opLife) {
        return `Life (years) must be less than or equal to the operational life of project (${opLife} years).`;
    }
    return null;
};

const applyNotesMetadata = (finalRow: any, value: any, user: any) => {
    if (value) {
        const authorName =
            [user?.first_name, user?.last_name].filter(Boolean).join(" ") ||
            user?.email ||
            "";
        return {
            ...finalRow,
            notes_author: authorName,
            notes_date: new Date().toISOString(),
        };
    }
    return { ...finalRow, notes_author: null, notes_date: null };
};

export function createMitigationOnCellChange(
    deps: MitigationInlineEditDeps,
): MitigationInlineCellChangeFactory {
    const { computeEmissionsForRow, getCalcConfig, user, fugitiveList } = deps;

    return (
        tableKey: string,
        setRows: React.Dispatch<React.SetStateAction<any[]>>,
        setTableError?: (msg: string | null) => void,
    ) =>
        async ({ id, key, value, item }: any) => {
            try {
            const tk = tableKey as UploadKey;
            let finalRow = { ...item, [key]: value };
            const cfg = getCalcConfig(tk);

            if (isElectricityTable(tk)) {
                const electricityTriggerKeys = new Set([
                    "emission_source",
                    "year",
                    "quantity_mwh",
                ]);
                if (electricityTriggerKeys.has(String(key))) {
                    const updatedRow = { ...item, [key]: value };
                    const yearError = validateElectricityYear(tk, updatedRow, deps);
                    if (yearError) {
                        setTableError?.(yearError);
                        setRows((prev) =>
                            prev.map((r) => (r.id === id ? { ...r, ...updatedRow } : r)),
                        );
                        return;
                    }
                    setTableError?.(null);
                    if (
                        updatedRow.emission_source &&
                        updatedRow.year &&
                        updatedRow.quantity_mwh
                    ) {
                        const calc = await computeEmissionsForRow(tk, updatedRow);
                        if (!calc) return;
                        const nextRow = {
                            ...updatedRow,
                            ...calc,
                            location_based_tco2e: calc.location_based_tco2e ?? null,
                            market_based_tco2e: calc.market_based_tco2e ?? null,
                            unit_display: "MWh",
                        };
                        setRows((prev) =>
                            prev.map((r) => (r.id === id ? { ...r, ...nextRow } : r)),
                        );
                    } else {
                        setRows((prev) =>
                            prev.map((r) => (r.id === id ? { ...r, ...updatedRow } : r)),
                        );
                    }
                } else {
                    setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));
                }
                return;
            }

            if (tk === "useB1G2" && String(key) === "application_type_id") {
                const eq = fugitiveList.find((e: any) => e.id === value);
                setRows((prev) =>
                    prev.map((row) =>
                        row.id === id
                            ? {
                                  ...row,
                                  application_type_id: value,
                                  application_type: eq?.equipment_type ?? "",
                                  annual_leakage_rate_percent: eq
                                      ? parseFloat(eq.default_annual_leakage_rate)
                                      : null,
                              }
                            : row,
                    ),
                );
                return;
            }

            if (tk === "componentRepl") {
                const isComponentReplTrigger = cfg?.triggerKeys?.includes(String(key));
                if (isComponentReplTrigger) {
                    const lifeError = validateComponentReplLife(tk, finalRow, deps);
                    if (lifeError) {
                        setTableError?.(lifeError);
                        setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));
                        return;
                    }
                    setTableError?.(null);
                }
            }

            const isTrigger = !!cfg && cfg.triggerKeys.includes(String(key));

            if (isTrigger) {
                if (tk === "refurbishment") await fetchAllActiveMrFactors();

                const calcPatch = await computeEmissionsForRow(tk, finalRow);

                if (calcPatch) {
                    const requiredPresent = cfg
                        ? hasAllRequired(finalRow, cfg.requiredKeys)
                        : false;
                    const nextVal =
                        calcPatch.total_emissions_tco2e ?? calcPatch.emissions_tco2e;
                    const calcFailedButShouldHaveWorked =
                        requiredPresent && !isValidEmission(nextVal);
                    if (!calcFailedButShouldHaveWorked) {
                        finalRow = { ...finalRow, ...calcPatch };
                    }
                }

                setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));
                return;
            }

            if (String(key) === "notes") {
                finalRow = applyNotesMetadata(finalRow, value, user);
            }

            setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));
            } catch (e) {
                console.warn("Mitigation inline cell change failed:", tableKey, key, e);
            }
        };
}

export function createMitigationOnRowPatch(
    deps: MitigationInlineEditDeps,
): MitigationInlineRowPatchFactory {
    const { computeEmissionsForRow, getCalcConfig } = deps;

    return (
        tableKey: string,
        setRows: React.Dispatch<React.SetStateAction<any[]>>,
        setTableError?: (msg: string | null) => void,
    ) =>
        async ({ id, patch, item }: any) => {
            try {
            const tk = tableKey as UploadKey;
            if (
                tk === "concreteRegSimplified" ||
                tk === "concreteRegDetailed"
            ) {
                let finalRow = { ...item, ...patch };
                try {
                    const calcPatch = await computeEmissionsForRow(tk, finalRow);
                    if (calcPatch) finalRow = { ...finalRow, ...calcPatch };
                } catch {
                    /* preserve row without calc */
                }
                setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));
                return;
            }

            let finalRow = { ...item, ...patch };
            setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));

            if (isElectricityTable(tk)) {
                const yearError = validateElectricityYear(tk, finalRow, deps);
                if (yearError) {
                    setTableError?.(yearError);
                    return;
                }
                setTableError?.(null);
            }

            const cfg = getCalcConfig(tk);
            const touchedTrigger = cfg?.triggerKeys?.some((k: string) =>
                Object.prototype.hasOwnProperty.call(patch, k),
            );

            if (tk === "componentRepl" && touchedTrigger) {
                const lifeError = validateComponentReplLife(tk, finalRow, deps);
                if (lifeError) {
                    setTableError?.(lifeError);
                    return;
                }
                setTableError?.(null);
            }

            if (cfg && touchedTrigger) {
                const calcPatch = await computeEmissionsForRow(tk, finalRow);
                if (calcPatch) {
                    finalRow = { ...finalRow, ...calcPatch };
                    setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));
                }
            }
            } catch (e) {
                console.warn("Mitigation inline row patch failed:", tableKey, e);
            }
        };
}
