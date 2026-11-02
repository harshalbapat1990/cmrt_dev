import { describe, expect, it } from "vitest";
import {
  buildDataEntryStageUrl,
  buildStageNavigationOptions,
  RESULTS_DASHBOARD_VALUE,
} from "./stageNavigationOptions";

const instances = [
  { id: "design-1", stage: "DESIGN" as const, sequence: 2, num_reports_required: 1 },
  { id: "recurring-1", stage: "RECURRING" as const, sequence: 3, num_reports_required: 1 },
  { id: "business-1", stage: "BUSINESS_CASE" as const, sequence: 1, num_reports_required: 2 },
  { id: "construction-1", stage: "CONSTRUCTION" as const, sequence: 4, num_reports_required: 1 },
];

describe("buildStageNavigationOptions", () => {
  it("keeps accessible project stages ordered and expands report options", () => {
    const options = buildStageNavigationOptions(instances, "SMALL");

    expect(options.map(({ label }) => label)).toEqual([
      "Business case (1 of 2)",
      "Business case (2 of 2)",
      "Design",
      "Construction",
      "Results dashboard",
    ]);
    expect(options[1]).toMatchObject({ stageInstanceId: "business-1", reportNumber: 2 });
  });

  it("includes only the recurring stage for recurring projects", () => {
    expect(buildStageNavigationOptions(instances, "RECURRING").map(({ label }) => label)).toEqual([
      "Recurring",
      "Results dashboard",
    ]);
  });

  it("builds a stage route with project, stage instance, and report number", () => {
    const option = buildStageNavigationOptions(instances, "SMALL")[1];
    const url = buildDataEntryStageUrl("project 1", option);

    expect(url).toBe("/dataEntry?projectId=project+1&stageInstanceId=business-1&reportNumber=2");
  });

  it("does not navigate away when the dashboard option is selected", () => {
    const dashboard = buildStageNavigationOptions(instances, "SMALL").find(
      (option) => option.value === RESULTS_DASHBOARD_VALUE,
    );

    expect(dashboard && buildDataEntryStageUrl("project-1", dashboard)).toBeNull();
  });
});
