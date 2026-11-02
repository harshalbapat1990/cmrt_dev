import { useMemo } from "react";
import type { StageAccess, StageAccessLevel } from "@/types/authorization";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import type { ProjectOption } from "@/services/ProjectOptions.service";
import { canAdminStage, canEditStage } from "../stageAccessUi";
import { getRecurringActivities, groupRecurringRowsByActivity } from "../recurringSelectors";
import { STAGE_LABEL_TO_ENUM, SUBSTAGES_FOR } from "../stageConstants";
import type {
  ProjectClass,
  ReportingBoundary,
  StageCode,
  StageInstance,
  StageLabel,
  DataEntryRow,
} from "../dataEntryTypes";
import { buildStageNavigationOptions } from "../stageNavigationOptions";

interface Params {
  activeStage: StageLabel;
  activeReportNumber: number;
  stageInstances: StageInstance[];
  stageAccess: StageAccess[];
  projectOptions: ProjectOption[];
  projectClass: ProjectClass | null;
  selectedOptionByStage: Record<string, string>;
  constructionPeriods: ConstructionPeriod[];
  selectedConstructionMonth: string | null;
  designReportNum: number;
  reportingBoundaries: ReportingBoundary[];
  recurringRows: DataEntryRow[];
}

/** Keeps stage and report selection derivation out of the page render. */
export function useDataEntryStageContext({
  activeStage,
  activeReportNumber,
  stageInstances,
  stageAccess,
  projectOptions,
  projectClass,
  selectedOptionByStage,
  constructionPeriods,
  selectedConstructionMonth,
  designReportNum,
  reportingBoundaries,
  recurringRows,
}: Params) {
  const activeStageInstance = useMemo(() => {
    const stageCode = STAGE_LABEL_TO_ENUM[activeStage];
    return stageInstances.find((stage) => stage.stage === stageCode) ?? null;
  }, [stageInstances, activeStage]);

  const activeStageAccess: StageAccessLevel = useMemo(() => {
    if (!activeStageInstance?.id) return "NONE";
    return stageAccess.find((item) => item.stage_instance_id === activeStageInstance.id)?.access ?? "NONE";
  }, [activeStageInstance, stageAccess]);
  const isProjAdmin = canAdminStage(activeStageAccess);
  const isProjEditor = canEditStage(activeStageAccess);
  const canEditActiveStage = isProjEditor;

  const mitigationBucketStageEnum: StageCode = activeStage === "Construction" ? "CONSTRUCTION" : "DESIGN";
  const mitigationStageInstance = useMemo(
    () => stageInstances.find((stage) => stage.stage === mitigationBucketStageEnum) ?? null,
    [stageInstances, mitigationBucketStageEnum],
  );
  const mitigationOptionId = useMemo(() => {
    if (!mitigationStageInstance || !projectOptions.length) return null;
    const options = projectOptions.filter((option) =>
      option.stage_instance_id === mitigationStageInstance.id && option.report_number === activeReportNumber,
    );
    return options.find((option) => option.is_default)?.id ?? options[0]?.id ?? null;
  }, [mitigationStageInstance, projectOptions, activeReportNumber]);

  const designStageInstance = useMemo(
    () => stageInstances.find((stage) => stage.stage === "DESIGN") ?? null,
    [stageInstances],
  );
  const designReportNums = useMemo(() => {
    if (!designStageInstance) return [];
    const numbers = projectOptions
      .filter((option) => option.stage_instance_id === designStageInstance.id)
      .map((option) => option.report_number);
    return [...new Set(numbers)].sort((a, b) => a - b);
  }, [designStageInstance, projectOptions]);
  const designSeedOptionId = useMemo(() => {
    if (!designStageInstance) return null;
    const options = projectOptions.filter(
      (option) => option.stage_instance_id === designStageInstance.id && option.report_number === designReportNum,
    );
    return options.find((option) => option.is_default)?.id ?? options[0]?.id ?? null;
  }, [designStageInstance, projectOptions, designReportNum]);

  const activePeriod = useMemo(
    () => constructionPeriods.find((period) => period.id === selectedConstructionMonth) ?? null,
    [constructionPeriods, selectedConstructionMonth],
  );
  const recurringActivities = useMemo(() => getRecurringActivities(reportingBoundaries), [reportingBoundaries]);
  const recurringRowsByActivity = useMemo(
    () => groupRecurringRowsByActivity(reportingBoundaries, recurringRows),
    [reportingBoundaries, recurringRows],
  );

  const currentReportSubOptions = useMemo(() => {
    if (!activeStageInstance) return [];
    return projectOptions.filter(
      (option) => option.stage_instance_id === activeStageInstance.id && option.report_number === activeReportNumber,
    );
  }, [projectOptions, activeStageInstance, activeReportNumber]);
  const baseCaseOptions = useMemo(
    () => currentReportSubOptions.map((option) => ({ label: option.label, value: option.id })),
    [currentReportSubOptions],
  );
  const activeOptionId = useMemo(() => {
    if (!activeStageInstance || !currentReportSubOptions.length) return null;
    const override = selectedOptionByStage[activeStageInstance.id];
    if (override && currentReportSubOptions.some((option) => option.id === override)) return override;
    return currentReportSubOptions.find((option) => option.is_default)?.id ?? currentReportSubOptions[0].id;
  }, [activeStageInstance, currentReportSubOptions, selectedOptionByStage]);
  const activeOption = useMemo(
    () => projectOptions.find((option) => option.id === activeOptionId) ?? null,
    [projectOptions, activeOptionId],
  );
  const optionTotalEmissions = useMemo(() => {
    const value = activeOption?.total_emissions_tco2e;
    if (value == null || value === "" || Number.isNaN(Number(value))) return 0;
    return Number(value);
  }, [activeOption?.total_emissions_tco2e]);

  const enrichedStages = useMemo(() => {
    return buildStageNavigationOptions(stageInstances, projectClass);
  }, [stageInstances, projectClass]);
  const subStages = useMemo(() => SUBSTAGES_FOR(activeStage, projectClass), [activeStage, projectClass]);

  return {
    activeStageInstance,
    activeStageAccess,
    canEditActiveStage,
    isProjAdmin,
    isProjEditor,
    mitigationBucketStageEnum,
    mitigationStageInstance,
    mitigationOptionId,
    designStageInstance,
    designReportNums,
    designSeedOptionId,
    activePeriod,
    recurringActivities,
    recurringRowsByActivity,
    currentReportSubOptions,
    baseCaseOptions,
    activeOptionId,
    activeOption,
    optionTotalEmissions,
    enrichedStages,
    subStages,
  };
}
