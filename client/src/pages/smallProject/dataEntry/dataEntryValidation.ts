export const hasAllRequired = (row: any, keys: string[]): boolean =>
    keys.every((k) => row?.[k] !== undefined && row?.[k] !== null && row?.[k] !== "");

export const isValidEmission = (v: any): boolean => {
    if (v === "-" || v === "" || v == null) return false;
    const n = Number(v);
    return !Number.isNaN(n);
};

export const getApiErrorMessage = (e: any): string => {
    const detail = e?.response?.data?.detail;
    if (Array.isArray(detail)) {
        return detail.map((d: any) => d?.msg ?? JSON.stringify(d)).join(", ");
    }
    if (typeof detail === "string") return detail;
    return (
        e?.response?.data?.message ??
        e?.message ??
        "Emission calculation failed. Please try again."
    );
};

export type ElectricityYearWindow = {
    start: number | null;
    end: number | null;
    label: string;
};

export const getElectricityYearWindow = (
    tableKey: string,
    opts: {
        constructionStartDate: string | null;
        constructionEndDate: string | null;
        opsStartYear: number | null;
        operationalLifeYears: number | null;
    }
): ElectricityYearWindow => {
    const { constructionStartDate, constructionEndDate, opsStartYear, operationalLifeYears } = opts;

    if (tableKey === "electricity") {
        const start = constructionStartDate ? new Date(constructionStartDate).getFullYear() : null;
        const end = constructionEndDate ? new Date(constructionEndDate).getFullYear() : null;
        const label =
            start && end ? `construction period (${start}–${end})` : "the construction period";
        return { start, end, label };
    }

    if (tableKey === "opEnergyElectricity") {
        const start = opsStartYear ?? null;
        const end =
            opsStartYear && operationalLifeYears
                ? opsStartYear + operationalLifeYears - 1
                : null;
        const label =
            start && end ? `operational period (${start}–${end})` : "the operational period";
        return { start, end, label };
    }

    return { start: null, end: null, label: "" };
};

export const validateElectricityYear = (
    tableKey: string,
    row: any,
    windowOpts: Parameters<typeof getElectricityYearWindow>[1]
): string | null => {
    const year = Number(row?.year);
    if (!Number.isFinite(year)) return null;

    const { start, end, label } = getElectricityYearWindow(tableKey, windowOpts);
    if (!start || !end) return null;

    if (year < start || year > end) {
        return `Year must be within ${label}.`;
    }
    return null;
};

export const validateComponentReplLife = (
    tableKey: string,
    row: any,
    operationalLifeYears: number | null
): string | null => {
    if (tableKey !== "componentRepl") return null;

    const rawLife = row?.life;
    if (rawLife === undefined || rawLife === null || rawLife === "") return null;

    const life = Number(rawLife);
    if (!Number.isFinite(life) || life <= 0) {
        return "Life must be a positive number.";
    }

    const opLife = Number(operationalLifeYears);
    if (life >= opLife) {
        return `Life (${life} yrs) must be less than the project operational life (${opLife} yrs).`;
    }
    return null;
};
