import type { StageCode, StageLabel } from "./dataEntryTypes";

export type { ProjectClass, StageCode, StageLabel } from "./dataEntryTypes";

export type UploadKey =
    | "asset"
    | "component"
    | "componentRepl"
    | "refurbishment"
    | "replDetailed"
    | "opEnergy"
    | "opEnergyDetailed"
    | "opEnergyElectricity"
    | "constructionG2"
    | "constructionG3"
    | "bcDetailedLevel"
    | "electricity"
    | "useB1G2"
    | "useB1G3"
    | "concreteRegSimplified"
    | "concreteRegDetailed"
    | "recurringG3";

const UPLOAD_KEYS: ReadonlySet<string> = new Set([
    "asset", "component", "componentRepl", "refurbishment", "replDetailed",
    "opEnergy", "opEnergyDetailed", "opEnergyElectricity", "constructionG2",
    "constructionG3", "bcDetailedLevel", "electricity", "useB1G2", "useB1G3",
    "concreteRegSimplified", "concreteRegDetailed", "recurringG3",
]);

export const isUploadKey = (value: string): value is UploadKey =>
    UPLOAD_KEYS.has(value);

export const ELECTRICITY_TABLE_KEYS: UploadKey[] = ["electricity", "opEnergyElectricity"];

const MITIGATION_SUBST_SUFFIXES = [
    "-mitigation-subst-replaced",
    "-mitigation-subst-adopted",
] as const;

/** Base electricity table key, stripping mitigation substitution leg suffixes when present. */
export const electricityBaseTableKey = (tableKey: string): UploadKey | null => {
    for (const suffix of MITIGATION_SUBST_SUFFIXES) {
        if (tableKey.endsWith(suffix)) {
            const base = tableKey.slice(0, -suffix.length);
            if (isUploadKey(base) && ELECTRICITY_TABLE_KEYS.includes(base)) {
                return base;
            }
        }
    }
    if (isUploadKey(tableKey) && ELECTRICITY_TABLE_KEYS.includes(tableKey)) {
        return tableKey;
    }
    return null;
};

export const isElectricityTable = (tableKey: string): boolean =>
    electricityBaseTableKey(tableKey) !== null;

const GRADE34_DETAILED_TABLE_KEYS = new Set([
    "bcDetailedLevel",
    "constructionG3",
    "recurringG3",
]);

export const isGrade34DetailedTable = (tableKey: string): boolean =>
    GRADE34_DETAILED_TABLE_KEYS.has(tableKey.split("-mitigation", 1)[0]);

export const MITIGATION_SUBMISSION_PERIOD_KEYS: UploadKey[] = [
    "constructionG2",
    "constructionG3",
    "electricity",
    "opEnergyElectricity",
    "useB1G2",
    "useB1G3",
    "componentRepl",
    "refurbishment",
    "replDetailed",
    "opEnergy",
    "opEnergyDetailed",
];

export const COMPLETENESS_LABEL = "Completeness";

   
const COMPLETENESS_STAGES = ["Business case", "Design", "Construction"] as const;

export const shouldShowCompletenessTab = (
    stageName: string,
    projectClass?: string | null
): boolean => {
    if (projectClass === "RECURRING") return false;
    if (projectClass !== "SMALL" && projectClass !== "LARGE") return false;
    return COMPLETENESS_STAGES.includes(stageName as (typeof COMPLETENESS_STAGES)[number]);
};

const MITIGATIONS_STAGES = ["Design", "Construction"] as const;

export const shouldShowMitigationsTab = (
    stageName: string,
    projectClass?: string | null
): boolean => {
    if (projectClass !== "LARGE") return false;
    return MITIGATIONS_STAGES.includes(stageName as (typeof MITIGATIONS_STAGES)[number]);
};


export const STAGE_ENUM_TO_LABEL: Record<StageCode, StageLabel> = {
    BUSINESS_CASE: "Business case",
    DESIGN: "Design",
    CONSTRUCTION: "Construction",
    RECURRING: "Recurring",
};

export const STAGE_LABEL_TO_ENUM: Record<StageLabel, StageCode> = {
    "Business case": "BUSINESS_CASE",
    Design: "DESIGN",
    Construction: "CONSTRUCTION",
    Recurring: "RECURRING",
};

export const REPLACEMENT_LABEL = "Replacement (B4) and Refurbishment (B5)";
export const REPLACEMENT_LABEL_LARGE =
    "Maintenance, Repair, Replacement and Refurbishment (B2-B5)";

export const SUBSTAGES_FOR = (stageName: string, pClass?: string | null): string[] => {
    const replacementLabel = pClass === "LARGE" ? REPLACEMENT_LABEL_LARGE : REPLACEMENT_LABEL;
    const base = ["Construction", replacementLabel, "Operational energy (B6)"];
    if (pClass === "LARGE") {
        base.splice(1, 0, "Use (B1)");
    }
    if (stageName === "Business case") return [...base, "Users (B8)"];
    if (stageName === "Design" ) {
        if (pClass === "LARGE") {
            return [...base, "Users (B8)"];
        }
        return [...base];
    }
    if (stageName === "Construction" && pClass === "LARGE") {
        return [
            "Construction",
            "Use (B1)",
            REPLACEMENT_LABEL_LARGE,
            "Operational energy (B6) and Water (B7)",
        ];
    }
    return [];
};

export const GROUPS_FOR = (stageName: string, pClass?: string | null) => {
    if (stageName === "Business case" || stageName === "Design") {
        const replacementLabel = pClass === "LARGE" ? REPLACEMENT_LABEL_LARGE : REPLACEMENT_LABEL;
        const operationsChildren = [
            ...(pClass === "LARGE" ? ["Use (B1)"] : []),
            replacementLabel,
            "Operational energy (B6)",
        ];
        return [
            {
                header: "Operations & maintenance",
                childrenValues: operationsChildren,
            },
        ];
    }
    if (stageName === "Construction" && pClass === "LARGE") {
        return [
            {
                header: "Operations & maintenance (optional)",
                childrenValues: [
                    "Use (B1)",
                    REPLACEMENT_LABEL_LARGE,
                    "Operational energy (B6) and Water (B7)",
                ],
            },
        ];
    }
    return [];
};
