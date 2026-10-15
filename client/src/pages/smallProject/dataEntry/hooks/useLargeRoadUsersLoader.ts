import { useEffect } from "react";
import ActivityDataService from "@/services/ActivityData.service";
import { normalizeCalculationSummary } from "../roadUserCalculations";
import type { RoadParams, RoadUserYearData } from "../roadUserTypes";
import { buildLargeRoadUserYears } from "../largeRoadUsersData";

interface UseLargeRoadUsersLoaderParams {
  stageInstanceId: string;
  optionId?: string | null;
  refreshKey?: number;
  projectMitigationId?: string | null;
  scopeUiTableKey: (base: string) => string;
  vehicleTypes: string[];
  largeUsersYears: number[];
  defaultParams: RoadParams;
  setGlobalParams: (params: RoadParams) => void;
  setYearData: (data: Record<number, RoadUserYearData>) => void;
  setEmissionSummary: (summary: ReturnType<typeof normalizeCalculationSummary>) => void;
}

export function useLargeRoadUsersLoader({
  stageInstanceId,
  optionId,
  refreshKey,
  projectMitigationId,
  scopeUiTableKey,
  vehicleTypes,
  largeUsersYears,
  defaultParams,
  setGlobalParams,
  setYearData,
  setEmissionSummary,
}: UseLargeRoadUsersLoaderParams) {
  useEffect(() => {
    if (!stageInstanceId) return;
    let cancelled = false;
    void (async () => {
      try {
        const [paramsRows, userRows] = await Promise.all([
          ActivityDataService.fetchRows(stageInstanceId, scopeUiTableKey("largeRoadParams"), optionId ?? null, undefined, projectMitigationId ?? undefined),
          ActivityDataService.fetchRows(stageInstanceId, scopeUiTableKey("largeRoadUsers"), optionId ?? null, undefined, projectMitigationId ?? undefined),
        ]);
        if (cancelled) return;
        const { globalParams, years, summaryFields } = buildLargeRoadUserYears(
          paramsRows,
          userRows,
          vehicleTypes,
          largeUsersYears,
          defaultParams,
        );
        setGlobalParams(globalParams);
        setEmissionSummary(normalizeCalculationSummary(summaryFields));
        setYearData(years);
      } catch (error) {
        if (!cancelled) console.error("Failed to load large road users data:", error);
      }
    })();
    return () => { cancelled = true; };
  }, [stageInstanceId, optionId, refreshKey, projectMitigationId, scopeUiTableKey, vehicleTypes, largeUsersYears, defaultParams, setGlobalParams, setYearData, setEmissionSummary]);
}
