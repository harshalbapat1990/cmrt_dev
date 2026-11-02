import { describe, expect, it } from "vitest";
import {
  canAdminStage,
  canEditStage,
  canShowCompleteness,
  canShowMitigations,
  canViewStage,
  filterAccessibleStageInstances,
  canRequestStageReopen,
} from "./stageAccessUi";

const instance = (id: string) => ({ id, stage: id });

const access = (stage_instance_id: string, level: "NONE" | "VIEW" | "EDIT" | "ADMIN") => ({
  stage_instance_id,
  stage: stage_instance_id,
  stage_label: stage_instance_id,
  sequence: 1,
  access: level,
});

describe("stage access helpers", () => {
  it("applies the VIEW < EDIT < ADMIN access hierarchy", () => {
    expect(canViewStage("VIEW")).toBe(true);
    expect(canEditStage("VIEW")).toBe(false);
    expect(canAdminStage("VIEW")).toBe(false);

    expect(canViewStage("EDIT")).toBe(true);
    expect(canEditStage("EDIT")).toBe(true);
    expect(canAdminStage("EDIT")).toBe(false);

    expect(canViewStage("ADMIN")).toBe(true);
    expect(canEditStage("ADMIN")).toBe(true);
    expect(canAdminStage("ADMIN")).toBe(true);

    expect(canViewStage("NONE")).toBe(false);
  });

  it("filters stage navigation to stages with at least VIEW access", () => {
    const instances = [instance("bc"), instance("design"), instance("construction"), instance("recurring")];
    const stageAccess = [
      access("bc", "NONE"),
      access("design", "VIEW"),
      access("construction", "EDIT"),
      access("recurring", "ADMIN"),
    ];

    expect(filterAccessibleStageInstances(instances, stageAccess).map((item) => item.id)).toEqual([
      "design",
      "construction",
      "recurring",
    ]);
  });

  it("allows reopen requests only for approved stages with EDIT access and no stage-admin role", () => {
    expect(canRequestStageReopen("VIEW", false, true)).toBe(false);
    expect(canRequestStageReopen("EDIT", false, false)).toBe(false);
    expect(canRequestStageReopen("EDIT", true, true)).toBe(false);
    expect(canRequestStageReopen("EDIT", false, true)).toBe(true);
    expect(canRequestStageReopen("ADMIN", false, true)).toBe(true);
  });

  it("shows Mitigations only for LARGE Design/Construction stages with view access", () => {
    expect(canShowMitigations("Design", "LARGE", "VIEW")).toBe(true);
    expect(canShowMitigations("Construction", "LARGE", "EDIT")).toBe(true);
    expect(canShowMitigations("Construction", "LARGE", "ADMIN")).toBe(true);

    expect(canShowMitigations("Design", "LARGE", "NONE")).toBe(false);
    expect(canShowMitigations("Business case", "LARGE", "ADMIN")).toBe(false);
    expect(canShowMitigations("Design", "SMALL", "ADMIN")).toBe(false);
  });

  it("shows Completeness only for supported stages, Australia, and view access", () => {
    for (const stage of ["Business case", "Design", "Construction"]) {
      expect(canShowCompleteness(stage, "SMALL", "Australia", "VIEW")).toBe(true);
      expect(canShowCompleteness(stage, "LARGE", "Australia", "EDIT")).toBe(true);
    }

    expect(canShowCompleteness("Design", "SMALL", "Australia", "NONE")).toBe(false);
    expect(canShowCompleteness("Recurring", "LARGE", "Australia", "ADMIN")).toBe(false);
    expect(canShowCompleteness("Design", "RECURRING", "Australia", "ADMIN")).toBe(false);
    expect(canShowCompleteness("Design", "LARGE", "New Zealand", "ADMIN")).toBe(false);
  });
});
