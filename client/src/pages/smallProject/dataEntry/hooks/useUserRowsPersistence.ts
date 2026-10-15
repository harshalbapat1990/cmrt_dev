import { useCallback } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { ActivityDataCreate } from "@/services/ActivityData.service";
import type { UserCalculationSummary } from "../roadUserCalculations";
import { persistUserActivityRows } from "../roadUserWorkflow";
import { useSaveStatus } from "./useSaveStatus";

export interface PersistedUserRow {
  id: string;
  vehicleType: string;
}

interface Params<Row extends PersistedUserRow> {
  readOnly: boolean;
  stageInstanceId: string;
  tableKey: string;
  projectMitigationId: string | null;
  setRows: Dispatch<SetStateAction<Row[]>>;
  buildPayload: (rows: Row[], summary?: UserCalculationSummary) => ActivityDataCreate[];
  onTotalsUpdated?: () => void | Promise<void>;
  errorLabel: string;
}

export function useUserRowsPersistence<Row extends PersistedUserRow>({
  readOnly,
  stageInstanceId,
  tableKey,
  projectMitigationId,
  setRows,
  buildPayload,
  onTotalsUpdated,
  errorLabel,
}: Params<Row>) {
  const [saveState, setSaveState] = useSaveStatus();

  const persistRows = useCallback(async (
    rows: Row[],
    summary?: UserCalculationSummary,
  ) => {
    if (readOnly) return;
    setSaveState("saving");
    try {
      const payload = buildPayload(rows, summary);
      if (payload.length === 0) {
        setSaveState("idle");
        return;
      }
      const saved = await persistUserActivityRows(
        stageInstanceId,
        tableKey,
        payload,
        projectMitigationId ?? undefined,
      );
      setRows((previous) => previous.map((row) => {
        const savedRow = saved.find((candidate) =>
          candidate.extra_fields?.vehicle_type === row.vehicleType
        );
        return savedRow ? { ...row, id: savedRow.id } : row;
      }));
      await onTotalsUpdated?.();
      setSaveState("saved");
    } catch (error) {
      console.error(`Failed to save ${errorLabel}:`, error);
      setSaveState("idle");
    }
  }, [
    readOnly,
    setSaveState,
    buildPayload,
    stageInstanceId,
    tableKey,
    projectMitigationId,
    setRows,
    onTotalsUpdated,
    errorLabel,
  ]);

  return { saveState, persistRows };
}
