import { useCallback, useEffect, useRef } from "react";
import type { Dispatch, SetStateAction } from "react";
import { toNumberOrNull } from "../roadUserCalculations";
import type { RailUserRow } from "../userDataMapping";
import { calculateRailUserRow } from "../roadUserWorkflow";
import { scheduleDebouncedTask } from "../roadUserDebounce";

const RAIL_CALC_DEBOUNCE_MS = 800;
const RAIL_SAVE_DEBOUNCE_MS = 800;

function isRailRowComplete(row: RailUserRow): boolean {
  return row.vehicleType !== "" && row.terrain !== "" && toNumberOrNull(row.freight) != null;
}

interface Params {
  projectId: string;
  setRows: Dispatch<SetStateAction<RailUserRow[]>>;
  persistRows: (rows: RailUserRow[]) => Promise<void>;
}

export function useRailUserCalculations({ projectId, setRows, persistRows }: Params) {
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestIds = useRef<Record<string, number>>({});

  const calculateAndPersistRow = useCallback(async (
    row: RailUserRow,
    allRows: RailUserRow[],
    requestKey: string,
  ) => {
    if (!isRailRowComplete(row)) return;

    requestIds.current[requestKey] = (requestIds.current[requestKey] ?? 0) + 1;
    const requestId = requestIds.current[requestKey];
    try {
      const calculatedRow = await calculateRailUserRow(projectId, row);
      if (requestIds.current[requestKey] !== requestId) return;

      const updatedRows = allRows.map((candidate) =>
        candidate.id === row.id ? calculatedRow : candidate,
      );
      setRows(updatedRows);
      await persistRows(updatedRows);
    } catch (error) {
      console.error("Failed to calculate rail emissions:", error);
    }
  }, [projectId, setRows, persistRows]);

  const scheduleCalculation = useCallback((
    row: RailUserRow,
    allRows: RailUserRow[],
    largeYear?: number | null,
  ) => {
    const requestKey = largeYear != null
      ? `${largeYear}-${row.vehicleType}`
      : row.vehicleType;
    scheduleDebouncedTask(timers.current, requestKey, RAIL_CALC_DEBOUNCE_MS, () => {
      void calculateAndPersistRow(row, allRows, requestKey);
    });
  }, [calculateAndPersistRow]);

  const scheduleSave = useCallback((rows: RailUserRow[]) => {
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      saveTimer.current = null;
      void persistRows(rows);
    }, RAIL_SAVE_DEBOUNCE_MS);
  }, [persistRows]);

  useEffect(() => () => {
    Object.values(timers.current).forEach(clearTimeout);
    if (saveTimer.current) clearTimeout(saveTimer.current);
  }, []);

  return { scheduleCalculation, scheduleSave };
}
