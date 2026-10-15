import type { DataEntryRow, ReportingBoundary } from "./dataEntryTypes";

export function getRecurringActivities(boundaries: ReportingBoundary[]): string[] {
    const seen = new Set<string>();
    const activities: string[] = [];
    for (const boundary of boundaries) {
        const activity = boundary.stage_or_activity ?? "";
        if (activity && !seen.has(activity)) {
            seen.add(activity);
            activities.push(activity);
        }
    }
    return activities;
}

export function groupRecurringRowsByActivity(
    boundaries: ReportingBoundary[],
    rows: DataEntryRow[],
): Record<string, DataEntryRow[]> {
    const grouped: Record<string, DataEntryRow[]> = {};
    for (const activity of getRecurringActivities(boundaries)) grouped[activity] = [];
    for (const row of rows) {
        const activity = resolveRecurringActivityForRow(row, boundaries);
        if (typeof activity === "string" && grouped[activity]) grouped[activity].push(row);
    }
    return grouped;
}

export function resolveRecurringActivityForRow(row: DataEntryRow, boundaries: ReportingBoundary[]): string | undefined {
    const boundaryId = row.reporting_boundary_id ?? row.extra_fields?.reporting_boundary_id;
    const boundaryActivity = typeof boundaryId === "string"
        ? boundaries.find((boundary) => boundary.id === boundaryId)?.stage_or_activity
        : undefined;
    const rowActivity = row.extra_fields?.stage_or_activity;
    return boundaryActivity ?? (typeof rowActivity === "string" ? rowActivity : undefined);
}
