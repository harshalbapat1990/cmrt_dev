import { useEffect } from "react";
import ActivityDataService from "@/services/ActivityData.service";
import { normalizeCalculationSummary, type UserCalculationSummary } from "../roadUserCalculations";
import type { RoadUserRow } from "../roadUserTypes";
import { mapRailUserRows, mapRoadUserRows, type RailUserRow } from "../userDataMapping";

interface UseUsersStageLoaderParams {
  stageInstanceId: string;
  optionId?: string | null;
  refreshKey?: number;
  projectMitigationId?: string | null;
  scopeUiTableKey: (base: string) => string;
  roadVehicleTypes: string[];
  initialRailRows: RailUserRow[];
  setRoadRows: (rows: RoadUserRow[]) => void;
  setRailRows: (rows: RailUserRow[]) => void;
  setRoadSummary: (summary: UserCalculationSummary) => void;
}

export function useUsersStageLoader({
  stageInstanceId,
  optionId,
  refreshKey,
  projectMitigationId,
  scopeUiTableKey,
  roadVehicleTypes,
  initialRailRows,
  setRoadRows,
  setRailRows,
  setRoadSummary,
}: UseUsersStageLoaderParams) {
  useEffect(() => {
    if (!stageInstanceId) return;
    let cancelled = false;
    void (async () => {
      try {
        const rows = await ActivityDataService.fetchRows(
          stageInstanceId,
          scopeUiTableKey("roadUsers"),
          optionId ?? null,
          undefined,
          projectMitigationId ?? undefined,
        );
        if (cancelled) return;
        setRoadSummary(normalizeCalculationSummary(rows.find((row) => row.extra_fields)?.extra_fields));
        setRoadRows(mapRoadUserRows(rows, roadVehicleTypes));
      } catch (error) {
        if (!cancelled) console.error("Failed to load road users data:", error);
      }
    })();
    return () => { cancelled = true; };
  }, [stageInstanceId, optionId, refreshKey, projectMitigationId, scopeUiTableKey, roadVehicleTypes, setRoadRows, setRoadSummary]);

  useEffect(() => {
    if (!stageInstanceId) return;
    let cancelled = false;
    void (async () => {
      try {
        const rows = await ActivityDataService.fetchRows(
          stageInstanceId,
          scopeUiTableKey("railUsers"),
          optionId ?? null,
          undefined,
          projectMitigationId ?? undefined,
        );
        if (!cancelled) setRailRows(mapRailUserRows(rows, initialRailRows));
      } catch (error) {
        if (!cancelled) console.error("Failed to load rail users data:", error);
      }
    })();
    return () => { cancelled = true; };
  }, [stageInstanceId, optionId, refreshKey, projectMitigationId, scopeUiTableKey, initialRailRows, setRailRows]);
}
