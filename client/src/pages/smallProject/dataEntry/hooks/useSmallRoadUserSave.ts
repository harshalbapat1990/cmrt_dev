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
    const saveStartedAt = performance.now();
    let calculationMs = 0;
    let persistenceMs = 0;
    try {
      if (buildPayload(rows)) {
        const calculationStartedAt = performance.now();
        const summary = await calculateSummary(rows);
        calculationMs = performance.now() - calculationStartedAt;
        if (!summary) {
          if (import.meta.env.DEV) {
            console.debug("[road users save timing] calculation did not produce a summary", {
              calculationMs: Math.round(calculationMs),
              totalMs: Math.round(performance.now() - saveStartedAt),
            });
          }
          return;
        }
        const persistenceStartedAt = performance.now();
        await persistRows(rows, summary);
        persistenceMs = performance.now() - persistenceStartedAt;
        if (import.meta.env.DEV) {
          console.debug("[road users save timing]", {
            calculationMs: Math.round(calculationMs),
            persistenceAndTotalsMs: Math.round(persistenceMs),
            totalMs: Math.round(performance.now() - saveStartedAt),
          });
        }
        return;
      }
      const persistenceStartedAt = performance.now();
      await persistRows(rows, currentSummary);
      persistenceMs = performance.now() - persistenceStartedAt;
      if (import.meta.env.DEV) {
        console.debug("[road users save timing]", {
          calculationMs: 0,
          persistenceAndTotalsMs: Math.round(persistenceMs),
          totalMs: Math.round(performance.now() - saveStartedAt),
        });
      }
    } catch (error) {
      console.error("Failed to save road users data:", error);
      if (import.meta.env.DEV) {
        console.debug("[road users save timing] failed", {
          calculationMs: Math.round(calculationMs),
          persistenceAndTotalsMs: Math.round(persistenceMs),
          totalMs: Math.round(performance.now() - saveStartedAt),
        });
      }
    }
  }, [readOnly, rows, currentSummary, buildPayload, calculateSummary, persistRows]);
}
