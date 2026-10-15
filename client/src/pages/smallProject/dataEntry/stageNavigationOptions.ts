import { STAGE_ENUM_TO_LABEL } from "./stageConstants";
import type { ProjectClass, StageInstance, StageLabel } from "./dataEntryTypes";

export const RESULTS_DASHBOARD_VALUE = "RESULTS_DASHBOARD";

export interface StageNavigationItem {
  label: string;
  value: string;
  stageLabel: StageLabel | typeof RESULTS_DASHBOARD_VALUE;
  reportNumber: number;
  disabled: boolean;
  stageInstanceId?: string;
}

/** Builds the shared project stage/report switcher options. */
export function buildStageNavigationOptions(
  stageInstances: StageInstance[],
  projectClass: ProjectClass | null,
): StageNavigationItem[] {
  const sorted = [...stageInstances]
    .filter((instance) => projectClass === "RECURRING"
      ? instance.stage === "RECURRING"
      : instance.stage !== "RECURRING")
    .sort((left, right) => (left.sequence ?? 0) - (right.sequence ?? 0));
  const items: StageNavigationItem[] = [];

  for (const instance of sorted) {
    const label = STAGE_ENUM_TO_LABEL[instance.stage];
    const reportCount = Math.max(1, instance.num_reports_required ?? 1);
    for (let reportNumber = 1; reportNumber <= reportCount; reportNumber += 1) {
      items.push({
        label: reportCount > 1 ? `${label} (${reportNumber} of ${reportCount})` : label,
        value: `${label}__${reportNumber}`,
        stageLabel: label,
        reportNumber,
        disabled: false,
        stageInstanceId: instance.id,
      });
    }
  }

  items.push({
    label: "Results dashboard",
    value: RESULTS_DASHBOARD_VALUE,
    stageLabel: RESULTS_DASHBOARD_VALUE,
    reportNumber: 1,
    disabled: false,
  });
  return items;
}

export function buildDataEntryStageUrl(projectId: string, item: StageNavigationItem): string | null {
  if (item.stageLabel === RESULTS_DASHBOARD_VALUE || !item.stageInstanceId) return null;
  const params = new URLSearchParams({
    projectId,
    stageInstanceId: item.stageInstanceId,
    reportNumber: String(item.reportNumber),
  });
  return `/dataEntry?${params.toString()}`;
}
