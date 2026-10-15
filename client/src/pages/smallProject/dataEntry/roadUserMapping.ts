import type { ActivityDataOut } from "@/services/ActivityData.service";
import type { RoadUserRow } from "./roadUserTypes";

function toText(value: unknown): string {
  return value == null ? "" : String(value);
}

/** Map persisted activity data into the shared editable road-user row shape. */
export function activityToRoadUserRow(
  activity: ActivityDataOut,
  vehicleType: string,
  fallbackId: string,
): RoadUserRow {
  const fields = activity.extra_fields ?? {};
  const lastEdited = fields.last_edited;

  return {
    id: activity.id || fallbackId,
    vehicleType,
    vkt: toText(fields.vkt),
    vht: toText(fields.vht),
    avgSpeed: toText(fields.avg_speed),
    lastEdited: lastEdited === "vht" || lastEdited === "avgSpeed" ? lastEdited : null,
    notes: toText(fields.notes),
  };
}
