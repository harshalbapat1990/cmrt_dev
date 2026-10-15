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
}

export function useLargeRoadUserSave({
  readOnly,
  region,
  yearData,
  roadParams,
  currentSummary,
  calculateSummary,
  persistAll,
}: Params) {
  const save = useCallback(async () => {
    if (readOnly) return;
    try {
      const calculatedSummary = await calculateSummary(yearData, region, roadParams);
      await persistAll(yearData, roadParams, calculatedSummary ?? currentSummary);
    } catch (error) {
      console.error("Failed to save large road users data:", error);
    }
  }, [readOnly, yearData, region, roadParams, currentSummary, calculateSummary, persistAll]);

  return save;
}
