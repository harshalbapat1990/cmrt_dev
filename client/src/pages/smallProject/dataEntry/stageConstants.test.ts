import { describe, expect, it } from "vitest";
import { GROUPS_FOR, SUBSTAGES_FOR, electricityBaseTableKey, isUploadKey } from "./stageConstants";

describe("data-entry stage navigation", () => {
  it("narrows table keys and resolves electricity mitigation keys safely", () => {
    expect(isUploadKey("electricity")).toBe(true);
    expect(isUploadKey("electricity-unknown")).toBe(false);
    expect(electricityBaseTableKey("electricity-mitigation-subst-adopted")).toBe("electricity");
    expect(electricityBaseTableKey("unknown-mitigation-subst-adopted")).toBeNull();
  });

  it("keeps stage tabs and child stages aligned for small and large projects", () => {
    expect(SUBSTAGES_FOR("Business case", "SMALL")).toEqual([
      "Construction",
      "Replacement (B4) and Refurbishment (B5)",
      "Operational energy (B6)",
      "Users (B8)",
    ]);
    expect(SUBSTAGES_FOR("Business case", "LARGE")).toContain("Use (B1)");
    expect(SUBSTAGES_FOR("Business case", "LARGE")).toContain("Users (B8)");
    expect(SUBSTAGES_FOR("Construction", "LARGE")).toEqual([
      "Construction",
      "Use (B1)",
      "Maintenance, Repair, Replacement and Refurbishment (B2-B5)",
      "Operational energy (B6) and Water (B7)",
    ]);
  });

  it("keeps recurring projects on the recurring workflow and groups optional operations", () => {
    expect(SUBSTAGES_FOR("Recurring", "RECURRING")).toEqual([]);
    expect(GROUPS_FOR("Business case", "LARGE")).toEqual([
      {
        header: "Operations & maintenance",
        childrenValues: [
          "Use (B1)",
          "Maintenance, Repair, Replacement and Refurbishment (B2-B5)",
          "Operational energy (B6)",
        ],
      },
    ]);
  });
});
