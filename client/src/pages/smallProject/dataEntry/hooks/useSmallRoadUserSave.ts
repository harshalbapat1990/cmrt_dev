import { useCallback } from "react";
import type { RoadUserRow } from "../roadUserTypes";
import type { UserCalculationSummary } from "../roadUserCalculations";
import type { RoadCalculationPayload } from "../userDataPayloads";

interface Params {
  readOnly: boolean;
  rows: RoadUserRow[];
  currentSummary: UserCalculationSummary;
  buildPayload: (rows: RoadUserRow[]) => RoadCalculationPayload | null;
  calculateSummary: (rows: RoadUserRow[]) => Promise<UserCalculationSummary | null>;
  persistRows: (rows: RoadUserRow[], summary: UserCalculationSummary) => Promise<void>;
}

export function useSmallRoadUserSave({
  readOnly,
  rows,
  currentSummary,
  buildPayload,
  calculateSummary,
  persistRows,
}: Params) {
  return useCallback(async () => {
    if (readOnly) return;
    try {
      if (buildPayload(rows)) {
        const summary = await calculateSummary(rows);
        if (!summary) return;
        await persistRows(rows, summary);
        return;
      }
      await persistRows(rows, currentSummary);
    } catch (error) {
      console.error("Failed to save road users data:", error);
    }
  }, [readOnly, rows, currentSummary, buildPayload, calculateSummary, persistRows]);
}
