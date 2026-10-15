import type { DataEntryRow } from "./dataEntryTypes";
import type { UploadKey } from "./stageConstants";

type UnknownRecord = Record<string, unknown>;

function asRecord(value: unknown): UnknownRecord | null {
    return typeof value === "object" && value !== null && !Array.isArray(value)
        ? value as UnknownRecord
        : null;
}

export const hasAllRequired = (row: DataEntryRow, keys: readonly string[]): boolean =>
    keys.every((key) => row[key] !== undefined && row[key] !== null && row[key] !== "");

export const isValidEmission = (value: unknown): boolean => {
    if (value === "-" || value === "" || value == null) return false;
    return !Number.isNaN(Number(value));
};

function formatErrorDetail(value: unknown): string {
    const record = asRecord(value);
    const message = record?.msg;
    if (typeof message === "string") return message;
    if (message != null) return JSON.stringify(message) ?? String(message);
    return JSON.stringify(value) ?? String(value);
}

export const getApiErrorMessage = (error: unknown): string => {
    const errorRecord = asRecord(error);
    const response = asRecord(errorRecord?.response);
    const data = asRecord(response?.data);
    const detail = data?.detail;
    if (Array.isArray(detail)) return detail.map(formatErrorDetail).join(", ");
    if (typeof detail === "string") return detail;
    if (typeof data?.message === "string") return data.message;
    if (error instanceof Error && error.message) return error.message;
    if (typeof errorRecord?.message === "string") return errorRecord.message;
    return "Emission calculation failed. Please try again.";
};

export type ElectricityYearWindow = {
    start: number | null;
    end: number | null;
    label: string;
};

export interface ElectricityYearOptions {
    constructionStartDate: string | null;
    constructionEndDate: string | null;
    opsStartYear: number | null;
    operationalLifeYears: number | null;
}

export const getElectricityYearWindow = (
    tableKey: UploadKey,
    opts: ElectricityYearOptions,
): ElectricityYearWindow => {
    const { constructionStartDate, constructionEndDate, opsStartYear, operationalLifeYears } = opts;

    if (tableKey === "electricity") {
        const start = constructionStartDate ? new Date(constructionStartDate).getFullYear() : null;
        const end = constructionEndDate ? new Date(constructionEndDate).getFullYear() : null;
        const label = start && end ? `construction period (${start}–${end})` : "the construction period";
        return { start, end, label };
    }

    if (tableKey === "opEnergyElectricity") {
        const start = opsStartYear ?? null;
        const end = opsStartYear && operationalLifeYears
            ? opsStartYear + operationalLifeYears - 1
            : null;
        const label = start && end ? `operational period (${start}–${end})` : "the operational period";
        return { start, end, label };
    }

    return { start: null, end: null, label: "" };
};

export const validateElectricityYear = (
    tableKey: UploadKey,
    row: DataEntryRow,
    windowOpts: ElectricityYearOptions,
): string | null => {
    const year = Number(row.year);
    if (!Number.isFinite(year)) return null;

    const { start, end, label } = getElectricityYearWindow(tableKey, windowOpts);
    if (!start || !end) return null;
    if (year < start || year > end) return `Year must be within ${label}.`;
    return null;
};

export const validateComponentReplLife = (
    tableKey: UploadKey,
    row: DataEntryRow,
    operationalLifeYears: number | null,
): string | null => {
    if (tableKey !== "componentRepl") return null;
    const rawLife = row.life;
    if (rawLife === undefined || rawLife === null || rawLife === "") return null;

    const life = Number(rawLife);
    if (!Number.isFinite(life) || life <= 0) return "Life must be a positive number.";
    const operationalLife = Number(operationalLifeYears);
    if (life >= operationalLife) {
        return `Life (${life} yrs) must be less than the project operational life (${operationalLife} yrs).`;
    }
    return null;
};

/** Narrow parser output to the application's row shape before passing it to editors. */
export function toDataEntryRows(rows: readonly unknown[]): DataEntryRow[] {
    return rows.filter((value): value is DataEntryRow => {
        const row = asRecord(value);
        if (!row) return false;
        const stringFields = [
            "mastertype_id", "typecast_id", "band_code", "emissions_category_id",
            "emissions_subcategory_id", "emission_subcategory_id", "metric_id",
            "dataset_revision_id", "unit_id", "reporting_boundary_id", "stage_or_activity",
        ] as const;
        const numericFields = [
            "quantity", "emissions_tco2e", "total_emissions_tco2e",
            "location_based_tco2e", "market_based_tco2e",
        ] as const;
        if (row.id !== undefined && typeof row.id !== "string" && typeof row.id !== "number") return false;
        if (stringFields.some((key) => key in row && row[key] !== null && typeof row[key] !== "string")) return false;
        if (numericFields.some((key) => key in row && row[key] !== null && typeof row[key] !== "string" && typeof row[key] !== "number")) return false;
        if ("extra_fields" in row && asRecord(row.extra_fields) === null) return false;
        if ("_fromApi" in row && typeof row._fromApi !== "boolean") return false;
        if ("_fromBoundary" in row && typeof row._fromBoundary !== "boolean") return false;
        return true;
    });
}
