import { describe, expect, it } from "vitest";
import type { DataEntryRow, ReportingBoundary } from "./dataEntryTypes";
import { getRecurringActivities, groupRecurringRowsByActivity } from "./recurringSelectors";

const boundaries: ReportingBoundary[] = [
    { id: "road", stage_or_activity: "Roads", category: "Transport", sub_category: "Road" },
    { id: "rail", stage_or_activity: "Rail", category: "Transport", sub_category: "Rail" },
    { id: "road-2", stage_or_activity: "Roads", category: "Transport", sub_category: "Other road" },
];

describe("recurring row selectors", () => {
    it("returns unique activities in boundary order", () => {
        expect(getRecurringActivities(boundaries)).toEqual(["Roads", "Rail"]);
    });

    it("groups rows by boundary activity and falls back to row activity metadata", () => {
        const rows: DataEntryRow[] = [
            { id: "a", reporting_boundary_id: "road" },
            { id: "b", extra_fields: { reporting_boundary_id: "rail" } },
            { id: "c", extra_fields: { stage_or_activity: "Roads" } },
            { id: "unknown", reporting_boundary_id: "missing" },
        ];

        expect(groupRecurringRowsByActivity(boundaries, rows)).toEqual({
            Roads: [rows[0], rows[2]],
            Rail: [rows[1]],
        });
    });
});
