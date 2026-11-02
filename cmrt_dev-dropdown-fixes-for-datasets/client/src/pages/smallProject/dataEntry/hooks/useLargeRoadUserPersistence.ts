import { useCallback } from "react";
import type { RoadParams, RoadUserYearData } from "../roadUserTypes";
import type { UserCalculationSummary } from "../roadUserCalculations";
import { buildLargeRoadUserPersistencePayloads } from "../largeRoadUsersData";
import { persistUserActivityRows } from "../roadUserWorkflow";
import { useSaveStatus } from "./useSaveStatus";

interface Params {
  readOnly: boolean;
  stageInstanceId: string;
  projectId: string;
  projectOptionId?: string | null;
  projectMitigationId: string | null;
  paramsTableKey: string;
  usersTableKey: string;
  getModelledYears: (yearData: Record<number, RoadUserYearData>) => number[];
  defaultParams: RoadParams;
  defaultSummary: UserCalculationSummary;
  onTotalsUpdated?: () => void | Promise<void>;
}

export function useLargeRoadUserPersistence({
  readOnly,
  stageInstanceId,
  projectId,
  projectOptionId,
  projectMitigationId,
  paramsTableKey,
  usersTableKey,
  getModelledYears,
  defaultParams,
  defaultSummary,
  onTotalsUpdated,
}: Params) {
  const [saveState, setSaveState] = useSaveStatus();

  const persistAll = useCallback(async (
    yearData: Record<number, RoadUserYearData>,
    params: RoadParams = defaultParams,
    summary: UserCalculationSummary = defaultSummary,
  ) => {
    if (readOnly) return;
    setSaveState("saving");
    const persistenceStartedAt = performance.now();
    let paramsSaveMs = 0;
    let usersSaveMs = 0;
    let totalsRefreshMs = 0;
    try {
      const { paramsPayload, usersPayload } = buildLargeRoadUserPersistencePayloads({
        years: getModelledYears(yearData),
        yearData,
        params,
        summary,
        projectId,
        stageInstanceId,
        projectOptionId,
        paramsTableKey,
        usersTableKey,
        projectMitigationId,
      });

      if (paramsPayload.length > 0) {
        const paramsSaveStartedAt = performance.now();
        await persistUserActivityRows(
          stageInstanceId,
          paramsTableKey,
          paramsPayload,
          projectMitigationId ?? undefined,
        );
        paramsSaveMs = performance.now() - paramsSaveStartedAt;
      }
      if (usersPayload.length > 0) {
        const usersSaveStartedAt = performance.now();
        await persistUserActivityRows(
          stageInstanceId,
          usersTableKey,
          usersPayload,
          projectMitigationId ?? undefined,
        );
        usersSaveMs = performance.now() - usersSaveStartedAt;
      }
      const totalsRefreshStartedAt = performance.now();
      await onTotalsUpdated?.();
      totalsRefreshMs = performance.now() - totalsRefreshStartedAt;
      if (import.meta.env.DEV) {
        console.debug("[large road users persistence timing]", {
          paramsSaveMs: Math.round(paramsSaveMs),
          usersSaveMs: Math.round(usersSaveMs),
          totalsRefreshMs: Math.round(totalsRefreshMs),
          totalMs: Math.round(performance.now() - persistenceStartedAt),
        });
      }
      setSaveState("saved");
    } catch (error) {
      console.error("Failed to save large road users data:", error);
      if (import.meta.env.DEV) {
        console.debug("[large road users persistence timing] failed", {
          paramsSaveMs: Math.round(paramsSaveMs),
          usersSaveMs: Math.round(usersSaveMs),
          totalsRefreshMs: Math.round(totalsRefreshMs),
          totalMs: Math.round(performance.now() - persistenceStartedAt),
        });
      }
      setSaveState("idle");
    }
  }, [
    readOnly,
    setSaveState,
    defaultParams,
    defaultSummary,
    getModelledYears,
    projectId,
    stageInstanceId,
    projectOptionId,
    paramsTableKey,
    usersTableKey,
    projectMitigationId,
    onTotalsUpdated,
  ]);

  return { saveState, persistAll };
}
