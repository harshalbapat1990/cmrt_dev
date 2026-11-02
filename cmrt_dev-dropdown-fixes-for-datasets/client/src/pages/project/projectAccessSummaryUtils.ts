import type { StageAccess, StageAccessLevel } from "@/types/authorization";

export type ProjectStageSummarySource = {
  id: string;
  stage: string;
  sequence?: number;
};

export type ProjectStageConfigSource = {
  stage: string;
  enabled: boolean;
};

export type ProjectAccessSummaryStage = {
  id: string;
  name: string;
  access: StageAccessLevel;
};

const STAGE_NAMES: Record<string, string> = {
  BUSINESS_CASE: "Business Case",
  DESIGN: "Design",
  CONSTRUCTION: "Construction",
  RECURRING: "Recurring",
};

const ACCESS_NAMES: Record<StageAccessLevel, string> = {
  ADMIN: "Admin",
  EDIT: "Edit",
  VIEW: "View",
  NONE: "No access",
};

const STAGE_ORDER: Record<string, number> = {
  BUSINESS_CASE: 1,
  RECURRING: 1,
  DESIGN: 2,
  CONSTRUCTION: 3,
};

export function getProjectRoleSummary(roles: string[]): string {
  const labels: string[] = [];
  if (roles.includes("PROJECT_ADMIN")) labels.push("Project Admin");
  if (roles.includes("ORG_ADMIN")) labels.push("Organisation Admin");
  return labels.length > 0 ? labels.join(" and ") : "Stage assignments";
}

export function getAccessLevelLabel(access: StageAccessLevel | undefined): string {
  return ACCESS_NAMES[access ?? "NONE"];
}

export function buildProjectAccessSummaryStages(
  projectClass: string,
  stageInstances: ProjectStageSummarySource[],
  stageConfigs: ProjectStageConfigSource[],
  stageAccess: StageAccess[],
): ProjectAccessSummaryStage[] {
  const recurringProject = projectClass === "RECURRING";
  const enabledStages = new Set(
    stageConfigs.filter((config) => config.enabled).map((config) => config.stage),
  );
  const accessByStageId = new Map(
    stageAccess.map((assignment) => [assignment.stage_instance_id, assignment.access]),
  );

  return stageInstances
    .filter((instance) => recurringProject
      ? instance.stage === "RECURRING"
      : instance.stage !== "RECURRING" && enabledStages.has(instance.stage))
    .sort((left, right) =>
      (STAGE_ORDER[left.stage] ?? 99) - (STAGE_ORDER[right.stage] ?? 99)
      || (left.sequence ?? 0) - (right.sequence ?? 0),
    )
    .map((instance) => ({
      id: instance.id,
      name: STAGE_NAMES[instance.stage] ?? instance.stage,
      access: accessByStageId.get(instance.id) ?? "NONE",
    }));
}
