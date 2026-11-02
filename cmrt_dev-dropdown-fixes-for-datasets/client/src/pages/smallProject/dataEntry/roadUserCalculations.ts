export interface RoadUserMetrics {
    vkt: string;
    vht: string;
    avgSpeed: string;
    lastEdited: "vht" | "avgSpeed" | null;
}

export interface UserCalculationSummary {
    absoluteEmissions: unknown;
    baseCaseAbsoluteEmissions: unknown;
    relativeUserEmissions: unknown;
}

type UnknownRecord = Record<string, unknown>;

function asRecord(value: unknown): UnknownRecord {
    return typeof value === "object" && value !== null ? value as UnknownRecord : {};
}

export function computeDerived<T extends RoadUserMetrics>(row: T): T {
    const vehicleKilometres = Number.parseFloat(row.vkt);
    if (!Number.isFinite(vehicleKilometres) || vehicleKilometres <= 0) return row;

    if (row.lastEdited === "vht") {
        const vehicleHours = Number.parseFloat(row.vht);
        return {
            ...row,
            avgSpeed: Number.isFinite(vehicleHours) && vehicleHours > 0
                ? (vehicleKilometres / vehicleHours).toFixed(2)
                : "",
        };
    }
    if (row.lastEdited === "avgSpeed") {
        const speed = Number.parseFloat(row.avgSpeed);
        return {
            ...row,
            vht: Number.isFinite(speed) && speed > 0
                ? (vehicleKilometres / speed).toFixed(2)
                : "",
        };
    }
    return row;
}

export function toNumberOrNull(value: unknown): number | null {
    if (value === "" || value == null) return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
}

export function getSpeed(row: RoadUserMetrics): number | null {
    const explicitSpeed = toNumberOrNull(row.avgSpeed);
    if (explicitSpeed != null) return explicitSpeed;
    const vehicleKilometres = toNumberOrNull(row.vkt);
    const vehicleHours = toNumberOrNull(row.vht);
    return vehicleKilometres != null && vehicleHours != null && vehicleHours > 0
        ? vehicleKilometres / vehicleHours
        : null;
}

export function isRoadRowComplete(row: RoadUserMetrics): boolean {
    return toNumberOrNull(row.vkt) != null && getSpeed(row) != null;
}

export function normalizeCalculationSummary(summary: unknown): UserCalculationSummary {
    const value = asRecord(summary);
    return {
        absoluteEmissions:
            value.interim_total_tco2e ??
            value.absoluteEmissions ??
            value.absolute_emissions ??
            value.absolute_emissions_tco2e ??
            0,
        baseCaseAbsoluteEmissions:
            value.base_case_emissions_tco2e ??
            value.baseCaseAbsoluteEmissions ??
            value.base_case_absolute_emissions ??
            value.base_case_absolute_emissions_tco2e ??
            null,
        relativeUserEmissions:
            value.final_user_emissions_tco2e ??
            value.relativeUserEmissions ??
            value.relative_user_emissions ??
            value.relative_user_emissions_tco2e ??
            null,
    };
}

export function isNewZealandJurisdiction(jurisdiction?: string | null): boolean {
    const value = (jurisdiction ?? "").trim().toLowerCase();
    return value === "nz" || value === "nzl" || value.includes("new zealand");
}
