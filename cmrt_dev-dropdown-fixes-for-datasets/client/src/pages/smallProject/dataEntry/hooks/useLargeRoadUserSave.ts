import { useCallback } from "react";
import type { RoadParams, RoadUserYearData } from "../roadUserTypes";
import type { UserCalculationSummary } from "../roadUserCalculations";
import type { RoadCalculationRegion } from "../roadUserWorkflow";

interface Params {
  readOnly: boolean;
  region: RoadCalculationRegion;
  yearData: Record<number, RoadUserYearData>;
  roadParams: RoadParams;
  currentSummary: UserCalculationSummary;
  calculateSummary: (
    yearData: Record<number, RoadUserYearData>,
    region: RoadCalculationRegion,
    params: RoadParams,
  ) => Promise<UserCalculationSummary | null>;
  persistAll: (
    yearData: Record<number, RoadUserYearData>,
    params: RoadParams,
    summary: UserCalculationSummary,
  ) => Promise<void>;
  onError?: (error: unknown) => void;
}

export function useLargeRoadUserSave({
  readOnly,
  region,
  yearData,
  roadParams,
  currentSummary,
  calculateSummary,
  persistAll,
  onError,
}: Params) {
  const save = useCallback(async () => {
    if (readOnly) return;
    const saveStartedAt = performance.now();
    let calculationMs = 0;
    let persistenceMs = 0;
    try {
      const calculationStartedAt = performance.now();
      const calculatedSummary = await calculateSummary(yearData, region, roadParams);
      calculationMs = performance.now() - calculationStartedAt;
      const persistenceStartedAt = performance.now();
      await persistAll(yearData, roadParams, calculatedSummary ?? currentSummary);
      persistenceMs = performance.now() - persistenceStartedAt;
      if (import.meta.env.DEV) {
        console.debug("[large road users save timing]", {
          calculationMs: Math.round(calculationMs),
          persistenceAndTotalsMs: Math.round(persistenceMs),
          totalMs: Math.round(performance.now() - saveStartedAt),
        });
      }
    } catch (error) {
      console.error("Failed to save large road users data:", error);
      onError?.(error);
      if (import.meta.env.DEV) {
        console.debug("[large road users save timing] failed", {
          calculationMs: Math.round(calculationMs),
          persistenceAndTotalsMs: Math.round(persistenceMs),
          totalMs: Math.round(performance.now() - saveStartedAt),
        });
      }
    }
  }, [readOnly, yearData, region, roadParams, currentSummary, calculateSummary, persistAll, onError]);

  return save;
}
