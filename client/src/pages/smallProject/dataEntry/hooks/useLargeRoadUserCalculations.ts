import { useCallback, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { RoadParams, RoadUserYearData } from "../roadUserTypes";
import type { UserCalculationSummary } from "../roadUserCalculations";
import {
  buildLargeAusRoadCalculationPayload,
  buildLargeNzRoadCalculationPayload,
} from "../largeRoadUsersData";
import { calculateRoadUserSummary, type RoadCalculationRegion } from "../roadUserWorkflow";

interface Params {
  projectId: string;
  stageInstanceId: string;
  projectOptionId?: string | null;
  getModelledYears: (yearData: Record<number, RoadUserYearData>) => number[];
  setSummary: Dispatch<SetStateAction<UserCalculationSummary>>;
}

export function useLargeRoadUserCalculations({
  projectId,
  stageInstanceId,
  projectOptionId,
  getModelledYears,
  setSummary,
}: Params) {
  const [loading, setLoading] = useState(false);

  const calculateSummary = useCallback(async (
    yearData: Record<number, RoadUserYearData>,
    region: RoadCalculationRegion,
    params: RoadParams,
  ): Promise<UserCalculationSummary | null> => {
    const sharedInput = {
      years: getModelledYears(yearData),
      yearData,
      projectId,
      stageInstanceId,
      projectOptionId,
    };
    const payload = region === "NZ"
      ? buildLargeNzRoadCalculationPayload(sharedInput)
      : buildLargeAusRoadCalculationPayload({ ...sharedInput, params });
    if (!payload) return null;

    try {
      setLoading(true);
      const summary = await calculateRoadUserSummary(payload, region, "large");
      setSummary(summary);
      return summary;
    } catch (error) {
      console.error(
        region === "NZ"
          ? "NZ road calculation failed:"
          : "Failed to calculate large road user emissions:",
        error,
      );
      return null;
    } finally {
      setLoading(false);
    }
  }, [
    getModelledYears,
    projectId,
    stageInstanceId,
    projectOptionId,
    setSummary,
  ]);

  return { loading, calculateSummary };
}
