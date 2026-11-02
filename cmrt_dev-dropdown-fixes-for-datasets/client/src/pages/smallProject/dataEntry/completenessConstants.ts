export const COMPLETENESS_UI_TABLE_KEY = "completeness";

export const DEFAULT_COMPLETENESS_PCT = 80;

export const COMPLETENESS_MIN_PCT = 80;
export const COMPLETENESS_MAX_PCT = 100;

export const COMPLETENESS_RANGE_ERROR = "Allowed range is between 80 to 100";

export type CompletenessModuleKey =
    | "a1_a3"
    | "a4"
    | "a5"
    | "b1"
    | "b2_b5"
    | "b6"
    | "b7";

export interface CompletenessModuleDef {
    module: CompletenessModuleKey;
    label: string;
}

export const COMPLETENESS_MODULES: CompletenessModuleDef[] = [
    { module: "a1_a3", label: "A1-A3" },
    { module: "a4", label: "A4" },
    { module: "a5", label: "A5" },
    { module: "b1", label: "B1" },
    { module: "b2_b5", label: "B2-B5" },
    { module: "b6", label: "B6" },
    { module: "b7", label: "B7" },
];
