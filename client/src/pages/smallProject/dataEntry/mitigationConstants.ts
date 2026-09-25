/** Shared mitigation / activity_data ui_table_key helpers (avoid circular imports). */

export type MitigationSubmissionStage = "Design" | "Construction";

export type MitigationLifecyclePhaseKey =
  | "construction"
  | "operations_maintenance"
  | "users";

export type MitigationSubstitutionLeg = "replaced" | "adopted";

export const LARGE_OPERATIONS_MAINTENANCE_KEYS = [
  "useB1G2",
  "useB1G3",
  "componentRepl",
  "refurbishment",
  "replDetailed",
  "opEnergy",
  "opEnergyDetailed",
  "opEnergyElectricity",
] as const;

/** Activity `ui_table_key` bases for Users (B8) rows inside mitigation-scoped activity_data (LARGE projects). */
export const USERS_MITIGATION_PANEL_BASE_KEYS = [
  "largeRoadParams",
  "largeRoadUsers",
  "railUsers",
  "largeRailUsers",
] as const;

const _usersMitigationKeySet = new Set<string>(USERS_MITIGATION_PANEL_BASE_KEYS);

export function isUsersMitigationBaseKey(baseKey: string): boolean {
  return _usersMitigationKeySet.has(baseKey);
}

export function mitigationUiKey(
  baseKey: string,
  leg?: MitigationSubstitutionLeg | null,
): string {
  if (leg === "replaced") return `${baseKey}-mitigation-subst-replaced`;
  if (leg === "adopted") return `${baseKey}-mitigation-subst-adopted`;
  return `${baseKey}-mitigation`;
}

/** Base upload keys rendered in the mitigation modal for lifecycle + submission stage. */
export function getMitigationPanelBaseKeys(
  submissionStage: MitigationSubmissionStage,
  lifecyclePhase: MitigationLifecyclePhaseKey,
): string[] {
  if (lifecyclePhase === "users") {
    if (submissionStage !== "Design") return [];
    return [...USERS_MITIGATION_PANEL_BASE_KEYS];
  }
  if (lifecyclePhase === "operations_maintenance") {
     return [...LARGE_OPERATIONS_MAINTENANCE_KEYS];
  }
  if (submissionStage === "Design") {
    return [
      "component",
      "bcDetailedLevel",
      "electricity",
     "concreteRegSimplified",
    ];
  }
  return [
    "constructionG2",
    "constructionG3",
    "electricity",
    "concreteRegSimplified",
  ];
}