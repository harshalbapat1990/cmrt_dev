import type { DataEntryRow } from "./dataEntryTypes";
import { isElectricityTable, type UploadKey } from "./stageConstants";

export interface ElectricityYearWindow {
    start: number | null;
    end: number | null;
    label: string;
}

export interface ElectricityYearContext {
    constructionStartDate: string | null;
    constructionEndDate: string | null;
    opsStartYear: number | null;
    operationalLifeYears: number | null;
}

export function getYearFromValue(value: unknown): number | null {
    if (value == null || value === "") return null;
    if (typeof value === "number") return Number.isFinite(value) ? value : null;
    const str = String(value).trim();
    if (/^\d{4}$/.test(str)) return Number(str);
    const parsed = new Date(str);
    return Number.isNaN(parsed.getTime()) ? null : parsed.getFullYear();
}

export function getElectricityYearWindow(
    tableKey: UploadKey,
    context: ElectricityYearContext,
): ElectricityYearWindow {
    if (tableKey === "electricity") {
        return {
            start: getYearFromValue(context.constructionStartDate),
            end: getYearFromValue(context.constructionEndDate),
            label: "construction period",
        };
    }
    if (tableKey === "opEnergyElectricity") {
        const start = getYearFromValue(context.opsStartYear);
        const end = start && context.operationalLifeYears ? start + Number(context.operationalLifeYears) : null;
        return { start, end, label: "operational period" };
    }
    return { start: null, end: null, label: "" };
}

export function validateElectricityYear(
    tableKey: UploadKey,
    row: DataEntryRow,
    context: ElectricityYearContext,
): string | null {
    if (!isElectricityTable(tableKey)) return null;
    const year = Number(row.year);
    if (!Number.isFinite(year)) return null;
    const { start, end, label } = getElectricityYearWindow(tableKey, context);
    if (!start || !end) {
        return tableKey === "electricity"
            ? "Construction start and end year are required for electricity calculations."
            : "Operations start year and operational life are required for electricity calculations.";
    }
    if (year < start || year > end) return `Year must be between ${start} and ${end} for the ${label}.`;
    return null;
}

export function validateComponentReplLife(
    tableKey: UploadKey,
    row: DataEntryRow,
    operationalLifeYears: number | null,
): string | null {
    if (tableKey !== "componentRepl") return null;
    const rawLife = row.life;
    if (rawLife === undefined || rawLife === null || rawLife === "") return null;
    const life = Number(rawLife);
    if (!Number.isFinite(life) || life <= 0) return "Life (years) must be a valid positive number.";
    const opLife = Number(operationalLifeYears);
    if (life > opLife) {
        return `Life (years) must be less than or equal to the operational life of project (${opLife} years).`;
    }
    return null;
}
