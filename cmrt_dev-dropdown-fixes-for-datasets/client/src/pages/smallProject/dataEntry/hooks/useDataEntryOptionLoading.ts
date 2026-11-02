import { useCallback, useEffect, type Dispatch, type SetStateAction } from "react";
import type { StageAccess } from "@/types/authorization";
import type { ProjectOption } from "@/services/ProjectOptions.service";
import type { ProjectClass, StageInstance, StageLabel } from "../dataEntryTypes";

interface Params {
  enabled: boolean;
  activeStage: StageLabel;
  projectClass: ProjectClass | null;
  showMitigations: boolean;
  activeStageInstance: StageInstance | null;
  mitigationStageInstance: StageInstance | null;
  mitigationBucketStageEnum: string;
  designStageInstance: StageInstance | null;
  stageAccess: StageAccess[];
  projectOptions: ProjectOption[];
  loadStageOptions: (stageInstanceId: string, access: StageAccess["access"]) => Promise<ProjectOption[]>;
  refreshStageOptions: (stageInstanceId: string) => Promise<ProjectOption[]>;
  setSelectedOptionByStage: Dispatch<SetStateAction<Record<string, string>>>;
}

/** Loads project options for the active stage and the two cross-stage workflows that need them. */
export function useDataEntryOptionLoading({
  enabled,
  activeStage,
  projectClass,
  showMitigations,
  activeStageInstance,
  mitigationStageInstance,
  mitigationBucketStageEnum,
  designStageInstance,
  stageAccess,
  projectOptions,
  loadStageOptions,
  refreshStageOptions,
  setSelectedOptionByStage,
}: Params) {
  useEffect(() => {
    if (!enabled || !activeStageInstance || activeStage === "Construction") return;
    const access = stageAccess.find((item) => item.stage_instance_id === activeStageInstance.id)?.access ?? "NONE";
    const alreadyLoaded = projectOptions.some((option) => option.stage_instance_id === activeStageInstance.id);
    if (access === "NONE" || alreadyLoaded) return;
    void loadStageOptions(activeStageInstance.id, access).catch((error) => {
      console.warn("Failed to lazily load options for stage instance:", activeStageInstance.id, error);
    });
  }, [enabled, activeStageInstance, activeStage, stageAccess, projectOptions, loadStageOptions]);

  useEffect(() => {
    if (!enabled || projectClass !== "LARGE" || !showMitigations) return;
    if (!mitigationStageInstance?.id || mitigationBucketStageEnum === "CONSTRUCTION") return;
    if (activeStageInstance?.id === mitigationStageInstance.id) return;
    const access = stageAccess.find((item) => item.stage_instance_id === mitigationStageInstance.id)?.access ?? "NONE";
    const alreadyLoaded = projectOptions.some((option) => option.stage_instance_id === mitigationStageInstance.id);
    if (access === "NONE" || alreadyLoaded) return;
    void loadStageOptions(mitigationStageInstance.id, access).catch((error) => {
      console.warn("Failed to ensure options for mitigation stage instance:", mitigationStageInstance.id, error);
    });
  }, [
    enabled,
    projectClass,
    showMitigations,
    mitigationStageInstance?.id,
    mitigationBucketStageEnum,
    activeStageInstance?.id,
    stageAccess,
    projectOptions,
    loadStageOptions,
  ]);

  useEffect(() => {
    if (!enabled || activeStage !== "Construction" || projectClass !== "LARGE") return;
    if (!designStageInstance?.id) return;
    const access = stageAccess.find((item) => item.stage_instance_id === designStageInstance.id)?.access ?? "NONE";
    const alreadyLoaded = projectOptions.some((option) => option.stage_instance_id === designStageInstance.id);
    if (access === "NONE" || alreadyLoaded) return;
    void loadStageOptions(designStageInstance.id, access).catch((error) => {
      console.warn("Failed to load Design options for Construction seed feature:", error);
    });
  }, [enabled, activeStage, projectClass, designStageInstance, stageAccess, projectOptions, loadStageOptions]);

  const onOptionsChange = useCallback(async () => {
    if (!activeStageInstance) return;
    try {
      const options = await refreshStageOptions(activeStageInstance.id);
      setSelectedOptionByStage((previous) => {
        const stageId = activeStageInstance.id;
        if (!previous[stageId] || options.some((option) => option.id === previous[stageId])) return previous;
        const { [stageId]: _removed, ...rest } = previous;
        return rest;
      });
    } catch (error) {
      console.warn("Failed to refresh options:", error);
    }
  }, [activeStageInstance, refreshStageOptions, setSelectedOptionByStage]);

  return { onOptionsChange };
}
