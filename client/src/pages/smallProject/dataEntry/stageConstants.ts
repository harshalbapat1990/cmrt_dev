import { assetTableConfig } from "./assetConfig";
import { componentTableConfig } from "./componentConfig";
import { refurbishmentTableConfig } from "./refurbishmentTableConfig";
import { componentReplacementConfig } from "./componentReplacementConfig";
import { opEnergyTableConfig } from "./opEnergyTableConfig";
import { constructionG2Config } from "./constructionG2Config";
import { constructionG3Config } from "./constructionG3Config";
import { electricityConfig } from "./electricityConfig";
import { useB1G2Config } from "./useB1G2Config";
import { useB1G3Config } from "./useB1G3Config";
import { concreteRegSimplifiedConfig } from "./ConcreteRegSimplifiedConfig";
import { concreteRegDetailedConfig } from "./concreteRegDetailedConfig";

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
            if (ELECTRICITY_TABLE_KEYS.includes(base as UploadKey)) {
                return base as UploadKey;
            }
        }
    }
    if (ELECTRICITY_TABLE_KEYS.includes(tableKey as UploadKey)) {
        return tableKey as UploadKey;
    }
    return null;
};

export const isElectricityTable = (tableKey: string): boolean =>
    //ELECTRICITY_TABLE_KEYS.includes(tableKey as UploadKey);
    electricityBaseTableKey(tableKey) !== null;

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

export const TABLE_CONFIGS: Record<UploadKey, any> = {
    asset: (projectId: string) => assetTableConfig(projectId),
    component: (projectId: string) => componentTableConfig(projectId),
    componentRepl: (projectId: string) => componentReplacementConfig(projectId),
    refurbishment: () => refurbishmentTableConfig(null),
    replDetailed: (projectId: string) => useB1G3Config(projectId),
    opEnergy: opEnergyTableConfig,
    opEnergyDetailed: (projectId: string) => useB1G3Config(projectId, ["Fuels", "Water"]),
    opEnergyElectricity: electricityConfig,
    constructionG2: (projectId: string) => constructionG2Config(projectId),
    constructionG3: (projectId: string) => constructionG3Config(projectId),
    bcDetailedLevel: (projectId: string) => constructionG3Config(projectId),
    electricity: electricityConfig,
    useB1G2: (projectId: string) => useB1G2Config(null, projectId),
    useB1G3: (projectId: string) => useB1G3Config(projectId),
    concreteRegSimplified: concreteRegSimplifiedConfig,
    concreteRegDetailed: concreteRegDetailedConfig,
    recurringG3: (projectId: string) => constructionG3Config(projectId),
};

export const resolveTableConfig = (tableKey: UploadKey, projectId: string): any => {
    //const cfg = TABLE_CONFIGS[tableKey];
    const baseKey = electricityBaseTableKey(tableKey) ?? tableKey;
    const cfg = TABLE_CONFIGS[baseKey as UploadKey];
    return typeof cfg === "function" ? cfg(projectId) : cfg;
};

export const normalizeRules = (rules: any[]) =>
    rules.map((r: any) =>
        r?.lookup?.fetch
            ? {
                  ...r,
                  lookup: {
                      ...r.lookup,
                      fetch: async (ctx?: { row?: any }) => {
                          const res = await r.lookup.fetch(ctx);
                          return Array.isArray(res) ? res : [];
                      },
                  },
              }
            : r
    );

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


export const STAGE_ENUM_TO_LABEL: Record<string, string> = {
    BUSINESS_CASE: "Business case",
    DESIGN: "Design",
    CONSTRUCTION: "Construction",
    RECURRING: "Recurring",
};

export const STAGE_LABEL_TO_ENUM: Record<string, string> = {
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
