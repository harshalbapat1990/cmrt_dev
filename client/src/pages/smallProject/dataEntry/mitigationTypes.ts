export type MitigationLifecyclePhase = "construction" | "operations_maintenance" | "users";
export type MitigationType = "reduction" | "substitution";

export interface Mitigation {
  id: string;
  name: string;
  type: MitigationType;
  group?: string;
  notes?: string;
  estimatedSavingTco2e: number;
  lifecyclePhase: MitigationLifecyclePhase;
  lifecyclePhaseLabel: string;
}

export const MITIGATION_TYPE_LABEL: Record<MitigationType, string> = {
  reduction: "Avoidance/Reduction Initiative",
  substitution: "Substitution Initiative",
};

export const MITIGATION_LIFECYCLE_PHASE_LABEL: Record<MitigationLifecyclePhase, string> = {
  construction: "Construction",
  operations_maintenance: "Operations & Maintenance",
  users: "Users",
};
