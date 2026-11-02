import { ACCESS_RANK, type StageAccess, type StageAccessLevel } from "@/types/authorization";
import {
  shouldShowCompletenessTab,
  shouldShowMitigationsTab,
} from "./stageConstants";

export const canViewStage = (access: StageAccessLevel): boolean =>
  ACCESS_RANK[access] >= ACCESS_RANK.VIEW;

export const canEditStage = (access: StageAccessLevel): boolean =>
  ACCESS_RANK[access] >= ACCESS_RANK.EDIT;

export const canAdminStage = (access: StageAccessLevel): boolean =>
  ACCESS_RANK[access] >= ACCESS_RANK.ADMIN;

export const isStageViewOnly = (access: StageAccessLevel): boolean =>
  access === "VIEW";

export function filterAccessibleStageInstances<T extends { id: string }>(
  instances: T[],
  stageAccess: StageAccess[],
): T[] {
  const accessibleIds = new Set(
    stageAccess
      .filter((item) => canViewStage(item.access))
      .map((item) => item.stage_instance_id),
  );

  return instances.filter((instance) => accessibleIds.has(instance.id));
}

export const canRequestStageReopen = (
  access: StageAccessLevel,
  isStageAdmin: boolean,
  isApproved: boolean,
): boolean => canEditStage(access) && !isStageAdmin && isApproved;

export const canShowMitigations = (
  stageName: string,
  projectClass: string | null | undefined,
  access: StageAccessLevel,
): boolean =>
  shouldShowMitigationsTab(stageName, projectClass) && canViewStage(access);

export const canShowCompleteness = (
  stageName: string,
  projectClass: string | null | undefined,
  jurisdiction: string | null | undefined,
  access: StageAccessLevel,
): boolean =>
  shouldShowCompletenessTab(stageName, projectClass) &&
  jurisdiction === "Australia" &&
  canViewStage(access);
