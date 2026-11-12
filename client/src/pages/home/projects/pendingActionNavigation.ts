export interface PendingActionNavigationItem {
  project_id: string;
  stage_instance_id: string;
  report_number: number | null;
  workflow_source: "project_option" | "reporting_period";
  period_id: string | null;
}

export function pendingActionUrl(item: PendingActionNavigationItem): string {
  const params = new URLSearchParams({
    projectId: item.project_id,
    stageInstanceId: item.stage_instance_id,
  });
  if (item.workflow_source === "reporting_period" && item.period_id) {
    params.set("periodId", item.period_id);
  } else if (item.report_number != null) {
    params.set("reportNumber", String(item.report_number));
  }
  return `/dataEntry?${params.toString()}`;
}
