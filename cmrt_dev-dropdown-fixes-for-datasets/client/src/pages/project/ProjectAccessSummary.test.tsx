import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { StageAccess } from "@/types/authorization";
import { ProjectAccessSummary } from "./ProjectAccessSummary";
import {
  buildProjectAccessSummaryStages,
  getAccessLevelLabel,
  getProjectRoleSummary,
} from "./projectAccessSummaryUtils";

describe("project access summary", () => {
  it("labels project-wide administrator roles", () => {
    expect(getProjectRoleSummary(["PROJECT_ADMIN"])).toBe("Project Admin");
    expect(getProjectRoleSummary(["ORG_ADMIN"])).toBe("Organisation Admin");
    expect(getProjectRoleSummary(["PROJECT_ADMIN", "ORG_ADMIN"])).toBe("Project Admin and Organisation Admin");
    expect(getProjectRoleSummary(["PROJECT_EDITOR"])).toBe("Stage assignments");
  });

  it("maps effective stage levels and defaults missing assignments to no access", () => {
    expect(getAccessLevelLabel("ADMIN")).toBe("Admin");
    expect(getAccessLevelLabel("EDIT")).toBe("Edit");
    expect(getAccessLevelLabel("VIEW")).toBe("View");
    expect(getAccessLevelLabel("NONE")).toBe("No access");
    expect(getAccessLevelLabel(undefined)).toBe("No access");
  });

  it("includes only enabled ordinary project stages", () => {
    const result = buildProjectAccessSummaryStages(
      "SMALL",
      [
        { id: "construction", stage: "CONSTRUCTION", sequence: 3 },
        { id: "design", stage: "DESIGN", sequence: 2 },
        { id: "business", stage: "BUSINESS_CASE", sequence: 1 },
        { id: "recurring", stage: "RECURRING", sequence: 4 },
      ],
      [
        { stage: "BUSINESS_CASE", enabled: true },
        { stage: "DESIGN", enabled: true },
        { stage: "CONSTRUCTION", enabled: false },
      ],
      [
        { stage_instance_id: "business", stage: "BUSINESS_CASE", stage_label: "Business Case", sequence: 1, access: "EDIT" },
        { stage_instance_id: "design", stage: "DESIGN", stage_label: "Design", sequence: 2, access: "VIEW" },
      ] satisfies StageAccess[],
    );

    expect(result).toEqual([
      { id: "business", name: "Business Case", access: "EDIT" },
      { id: "design", name: "Design", access: "VIEW" },
    ]);
  });

  it("uses the recurring stage for recurring projects", () => {
    const result = buildProjectAccessSummaryStages(
      "RECURRING",
      [
        { id: "business", stage: "BUSINESS_CASE", sequence: 1 },
        { id: "recurring", stage: "RECURRING", sequence: 4 },
      ],
      [],
      [{ stage_instance_id: "recurring", stage: "RECURRING", stage_label: "Recurring", sequence: 1, access: "ADMIN" }] satisfies StageAccess[],
    );

    expect(result).toEqual([{ id: "recurring", name: "Recurring", access: "ADMIN" }]);
  });

  it("shows loading and access failure separately from a no-access result", () => {
    expect(ProjectAccessSummary).toBeDefined();
    const props = {
      roleSummary: "Stage assignments",
      stages: [],
    };
    const { rerender } = render(<ProjectAccessSummary {...props} loading error={null} />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading your access");

    rerender(<ProjectAccessSummary {...props} loading={false} error="Access service unavailable" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Access service unavailable");
    expect(screen.queryByText("No access")).toBeNull();
  });

  it("renders stage access as a table", () => {
    render(
      <ProjectAccessSummary
        loading={false}
        error={null}
        roleSummary="Project Admin"
        stages={[
          { id: "stage-1", name: "Business Case", access: "ADMIN" },
          { id: "stage-2", name: "Design", access: "NONE" },
        ]}
      />,
    );

    expect(screen.getByRole("table")).toBeTruthy();
    expect(screen.getByText("Project-wide access:")).toBeTruthy();
    expect(screen.getByText("Business Case")).toBeTruthy();
    expect(screen.getByText("Admin")).toBeTruthy();
    expect(screen.getByText("Design")).toBeTruthy();
    expect(screen.getByText("No access")).toBeTruthy();
  });
});
