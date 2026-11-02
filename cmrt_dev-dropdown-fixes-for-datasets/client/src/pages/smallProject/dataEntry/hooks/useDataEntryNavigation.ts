import { useCallback, type Dispatch, type SetStateAction } from "react";
import type { NavigateFunction } from "react-router-dom";
import { COMPLETENESS_LABEL, SUBSTAGES_FOR } from "../stageConstants";
import type { ProjectClass, ProjectDetails, StageLabel } from "../dataEntryTypes";
import type { StageNavigationItem } from "../stageNavigationOptions";

interface Params {
  projectId: string;
  projectData: ProjectDetails | null;
  projectClass: ProjectClass | null;
  activeSubStage: string;
  subStages: string[];
  stages: StageNavigationItem[];
  mitigationsEnabled: boolean;
  completenessEnabled: boolean;
  navigate: NavigateFunction;
  setActiveStage: Dispatch<SetStateAction<StageLabel>>;
  setActiveReportNumber: Dispatch<SetStateAction<number>>;
  setActiveSubStage: Dispatch<SetStateAction<string>>;
  setShowMitigations: Dispatch<SetStateAction<boolean>>;
  setShowCompleteness: Dispatch<SetStateAction<boolean>>;
  setShowAuditPanel: Dispatch<SetStateAction<boolean>>;
}

/** Owns stage, substage, and workflow-panel navigation transitions. */
export function useDataEntryNavigation({
  projectId,
  projectData,
  projectClass,
  activeSubStage,
  subStages,
  stages,
  mitigationsEnabled,
  completenessEnabled,
  navigate,
  setActiveStage,
  setActiveReportNumber,
  setActiveSubStage,
  setShowMitigations,
  setShowCompleteness,
  setShowAuditPanel,
}: Params) {
  const selectStage = useCallback((value: string) => {
    if (value === "RESULTS_DASHBOARD") {
      navigate(`/resultsDashboard?projectId=${projectId}`, { state: { projectData } });
      return;
    }
    const selected = stages.find((stage) => stage.value === value);
    if (!selected || selected.disabled || selected.stageLabel === "RESULTS_DASHBOARD") return;

    setActiveStage(selected.stageLabel);
    setActiveReportNumber(selected.reportNumber);
    const availableSubStages = SUBSTAGES_FOR(selected.stageLabel, projectClass);
    setActiveSubStage(availableSubStages[0] ?? "Construction");
    setShowMitigations(false);
    setShowCompleteness(false);
    setShowAuditPanel(false);
  }, [
    navigate,
    projectId,
    projectData,
    stages,
    projectClass,
    setActiveStage,
    setActiveReportNumber,
    setActiveSubStage,
    setShowMitigations,
    setShowCompleteness,
    setShowAuditPanel,
  ]);

  const selectSubStage = useCallback((value: string) => {
    setShowAuditPanel(false);
    setActiveSubStage(value);
    setShowMitigations(false);
    setShowCompleteness(false);
  }, [setShowAuditPanel, setActiveSubStage, setShowMitigations, setShowCompleteness]);

  const selectMitigations = useCallback(() => {
    if (!mitigationsEnabled) return;
    setShowMitigations(true);
    setShowCompleteness(false);
    setShowAuditPanel(false);
    setActiveSubStage("");
  }, [mitigationsEnabled, setShowMitigations, setShowCompleteness, setShowAuditPanel, setActiveSubStage]);

  const selectCompleteness = useCallback(() => {
    if (!completenessEnabled) return;
    setShowMitigations(false);
    setShowCompleteness(true);
    setActiveSubStage(COMPLETENESS_LABEL);
  }, [completenessEnabled, setShowMitigations, setShowCompleteness, setActiveSubStage]);

  const goToNextSubStage = useCallback(() => {
    const index = subStages.indexOf(activeSubStage);
    const next = index < 0 ? undefined : subStages[index + 1];
    if (next) setActiveSubStage(next);
  }, [subStages, activeSubStage, setActiveSubStage]);

  const goToPreviousSubStage = useCallback(() => {
    const index = subStages.indexOf(activeSubStage);
    if (index > 0) setActiveSubStage(subStages[index - 1]);
  }, [subStages, activeSubStage, setActiveSubStage]);

  const guardedAction = useCallback((action: "exit" | "next") => {
    if (action === "next") goToNextSubStage();
    if (action === "exit") navigate(`/projects/${projectId}`);
  }, [goToNextSubStage, navigate, projectId]);

  return {
    selectStage,
    selectSubStage,
    selectMitigations,
    selectCompleteness,
    goToNextSubStage,
    goToPreviousSubStage,
    guardedAction,
  };
}
