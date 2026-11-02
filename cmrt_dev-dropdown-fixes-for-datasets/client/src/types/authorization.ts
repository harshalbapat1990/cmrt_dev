export type StageAccessLevel = "NONE" | "VIEW" | "EDIT" | "ADMIN";

export type StageAccess = {
  stage_instance_id: string;
  stage: string;
  stage_label: string;
  sequence: number;
  access: StageAccessLevel;
  user_role_id?: string | null;
};

export type MyProjectAccess = {
  user_id: string;
  project_id: string | null;
  effective_roles: string[];
  stage_access: StageAccess[];
};

export type ProjectStageAssignment = {
  stage_instance_id: string;
  access: "VIEW" | "EDIT";
};

export type ProjectAccessMember = {
  user_id: string;
  display_name: string;
  email: string;
  assignments: StageAccess[];
};

export type ProjectAccess = {
  project_id: string;
  project_name: string;
  stages: StageAccess[];
  members: ProjectAccessMember[];
};

export const ACCESS_RANK: Record<StageAccessLevel, number> = {
  NONE: 0,
  VIEW: 10,
  EDIT: 20,
  ADMIN: 30,
};

export function getStageAccessLevel(
  stageAccess: StageAccess | undefined,
): StageAccessLevel {
  return stageAccess?.access ?? "NONE";
}

export function hasAtLeastStageAccess(
  stageAccess: StageAccess | undefined,
  minimum: StageAccessLevel,
): boolean {
  return ACCESS_RANK[getStageAccessLevel(stageAccess)] >= ACCESS_RANK[minimum];
}

export function isStageAccessible(
  stageAccess: StageAccess | undefined,
): boolean {
  return getStageAccessLevel(stageAccess) !== "NONE";
}
