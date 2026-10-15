import type { ProjectOption } from "@/services/ProjectOptions.service";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import type { StageAccessLevel } from "@/types/authorization";
import { canShowCompleteness, canShowMitigations } from "../stageAccessUi";
import { REPLACEMENT_LABEL, REPLACEMENT_LABEL_LARGE, STAGE_LABEL_TO_ENUM } from "../stageConstants";
import type { ProjectClass, StageCode, StageInstance, StageLabel } from "../dataEntryTypes";

interface Params {
  activeStage: StageLabel;
  activeSubStage: string;
  projectClass: ProjectClass | null;
  jurisdiction: string | null | undefined;
  activeStageAccess: StageAccessLevel;
  activeStageInstance: StageInstance | null;
  activeOption: ProjectOption | null;
  activePeriod: ConstructionPeriod | null;
  currentReportOptionCount: number;
  lockedStages: Set<StageCode>;
  projectClosed: boolean;
  canEditActiveStage: boolean;
  isProjAdmin: boolean;
  isProjEditor: boolean;
  showCompleteness: boolean;
  showMitigations: boolean;
  subStages: string[];
}

/** Centralizes stage status, editability, and workflow visibility rules. */
export function useDataEntryWorkflowViewState({
  activeStage,
  activeSubStage,
  projectClass,
  jurisdiction,
  activeStageAccess,
  activeStageInstance,
  activeOption,
  activePeriod,
  currentReportOptionCount,
  lockedStages,
  projectClosed,
  canEditActiveStage,
  isProjAdmin,
  isProjEditor,
  showCompleteness,
  showMitigations,
  subStages,
}: Params) {
  const isConstructionStage = activeStage === "Construction";
  const isRecurringStage = activeStage === "Recurring";
  const isBusinessCaseStage = activeStage === "Business case";
  const isDesignStage = activeStage === "Design";
  const isBcOrDesignStage = isBusinessCaseStage || isDesignStage;
  const isLargeProject = projectClass === "LARGE";
  const isSubStageConstruction = activeSubStage === "Construction";
  const isSubStageUseB1 = activeSubStage === "Use (B1)";
  const isSubStageReplacement = activeSubStage === REPLACEMENT_LABEL || activeSubStage === REPLACEMENT_LABEL_LARGE;
  const isSubStageOpEnergy = activeSubStage === "Operational energy (B6)";
  const isSubStageOpEnergyW = activeSubStage === "Operational energy (B6) and Water (B7)";
  const isUsersSubStage = (isBusinessCaseStage || isDesignStage) && activeSubStage === "Users (B8)";

  const currentStageEnum = STAGE_LABEL_TO_ENUM[activeStage];
  const isCurrentStageLocked = lockedStages.has(currentStageEnum);
  const status = activeOption?.approval_status ?? "draft";
  const isPeriodWorkflowStage = isConstructionStage || isRecurringStage;
  const periodStatus = activePeriod?.status;
  const isSubmitted = isPeriodWorkflowStage ? periodStatus === "awaiting_approval" : status === "submitted";
  const isApproved = isPeriodWorkflowStage ? periodStatus === "approved" : status === "final_approved";
  const isRejected = isPeriodWorkflowStage ? periodStatus === "rejected" : status === "rejected";
  const isReopenRequested = isPeriodWorkflowStage ? periodStatus === "reopen_requested" : status === "pending_reopen";

  const isConstructionPeriodReadOnly = periodStatus === "awaiting_approval" ||
    periodStatus === "approved" || periodStatus === "reopen_requested";
  const statusBasedReadOnly = isPeriodWorkflowStage
    ? isConstructionPeriodReadOnly
    : isSubmitted || isApproved || isReopenRequested;
  const adminViewOnly = isProjAdmin && !isProjEditor;
  const isOptionsReadyForStage = !isBusinessCaseStage && !isDesignStage
    ? true
    : !!activeStageInstance && currentReportOptionCount > 0;
  const isReadOnly = !canEditActiveStage || adminViewOnly || statusBasedReadOnly || projectClosed || !isOptionsReadyForStage;
  const isLastSubStage = subStages[subStages.length - 1] === activeSubStage;

  const mitigationsTabEnabled = canShowMitigations(activeStage, projectClass, activeStageAccess);
  const completenessEnabled = canShowCompleteness(activeStage, projectClass, jurisdiction, activeStageAccess);
  const completenessSubmissionStage = completenessEnabled && (isBusinessCaseStage || isDesignStage || isConstructionStage);
  const shouldShowSubmit = !adminViewOnly && !isReadOnly && (
    completenessSubmissionStage ? showCompleteness : isLastSubStage || isConstructionStage || isRecurringStage
  );
  const showMitigationsNextBtn = mitigationsTabEnabled && isLastSubStage && !adminViewOnly && !isReadOnly;
  const showCompletenessNextBtn = completenessSubmissionStage &&
    !showCompleteness && !showMitigations && !adminViewOnly && !isReadOnly && !showMitigationsNextBtn &&
    (isLastSubStage || (isConstructionStage && subStages.length === 0));
  const shouldShowMitigationSubmit = !adminViewOnly && !isReadOnly;

  return {
    currentStageEnum,
    isCurrentStageLocked,
    isUsersSubStage,
    status,
    isSubmitted,
    isApproved,
    isRejected,
    isReopenRequested,
    isConstructionPeriodReadOnly,
    statusBasedReadOnly,
    adminViewOnly,
    isOptionsReadyForStage,
    isReadOnly,
    isLastSubStage,
    isConstructionStage,
    isRecurringStage,
    isBusinessCaseStage,
    isDesignStage,
    isBcOrDesignStage,
    isLargeProject,
    mitigationsTabEnabled,
    completenessEnabled,
    completenessSubmissionStage,
    isSubStageConstruction,
    isSubStageUseB1,
    isSubStageReplacement,
    isSubStageOpEnergy,
    isSubStageOpEnergyW,
    shouldShowSubmit,
    showMitigationsNextBtn,
    showCompletenessNextBtn,
    shouldShowMitigationSubmit,
    isUsersReadOnly: isReadOnly,
    reopenReasonText: activeOption?.current_justification ?? "",
  };
}
