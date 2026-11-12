import { describe, expect, it } from "vitest";
import { pendingActionUrl } from "./pendingActionNavigation";

describe("pending action navigation", () => {
  it("opens a reporting period by its period ID", () => {
    expect(pendingActionUrl({
      project_id: "project 1",
      stage_instance_id: "recurring-stage",
      report_number: null,
      workflow_source: "reporting_period",
      period_id: "period-1",
    })).toBe("/dataEntry?projectId=project+1&stageInstanceId=recurring-stage&periodId=period-1");
  });

  it("retains project-option report navigation", () => {
    expect(pendingActionUrl({
      project_id: "project-1",
      stage_instance_id: "design-stage",
      report_number: 2,
      workflow_source: "project_option",
      period_id: null,
    })).toBe("/dataEntry?projectId=project-1&stageInstanceId=design-stage&reportNumber=2");
  });
});
