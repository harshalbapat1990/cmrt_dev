import { useCallback, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { RoadUserRow } from "../roadUserTypes";
import type { UserCalculationSummary } from "../roadUserCalculations";
import { buildRoadCalculationPayload } from "../userDataPayloads";
import type { UserActivityContext } from "../userDataPayloads";
import { calculateRoadUserSummary, type RoadCalculationRegion } from "../roadUserWorkflow";

interface Params extends UserActivityContext {
  region: RoadCalculationRegion;
  showRoad: boolean;
  isLargeProject: boolean;
  setSummary: Dispatch<SetStateAction<UserCalculationSummary>>;
}

export function useSmallRoadUserCalculations({
  projectId,
  stageInstanceId,
  projectOptionId,
  region,
  showRoad,
  isLargeProject,
  setSummary,
}: Params) {
  const [loading, setLoading] = useState(false);

  const buildPayload = useCallback((rows: RoadUserRow[]) =>
    buildRoadCalculationPayload(rows, { projectId, stageInstanceId, projectOptionId }),
  [projectId, stageInstanceId, projectOptionId]);

  const calculateSummary = useCallback(async (
    rows: RoadUserRow[],
  ): Promise<UserCalculationSummary | null> => {
    if (!showRoad || isLargeProject) return null;
    const payload = buildPayload(rows);
    if (!payload) return null;

    try {
      setLoading(true);
      const summary = await calculateRoadUserSummary(payload, region, "small");
      setSummary(summary);
      return summary;
    } catch (error) {
      console.error("Failed to calculate road user emissions:", error);
      return null;
    } finally {
      setLoading(false);
    }
  }, [showRoad, isLargeProject, buildPayload, region, setSummary]);

  return { loading, buildPayload, calculateSummary };
}
