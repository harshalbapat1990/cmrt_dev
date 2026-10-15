import { useCallback } from "react";
import type { Dispatch, SetStateAction } from "react";
import { computeDerived } from "../roadUserCalculations";
import type { RoadUserRow } from "../roadUserTypes";
import type { RailUserRow } from "../userDataMapping";

interface Params {
  readOnly: boolean;
  setRoadRows: Dispatch<SetStateAction<RoadUserRow[]>>;
  setRailRows: Dispatch<SetStateAction<RailUserRow[]>>;
  scheduleRailCalculation: (
    row: RailUserRow,
    rows: RailUserRow[],
    largeYear?: number | null,
  ) => void;
  scheduleRailSave: (rows: RailUserRow[]) => void;
}

export function useUsersRowEditing({
  readOnly,
  setRoadRows,
  setRailRows,
  scheduleRailCalculation,
  scheduleRailSave,
}: Params) {
  const updateRoadRow = useCallback((id: string, changes: Partial<RoadUserRow>) => {
    if (readOnly) return;
    setRoadRows((rows) => rows.map((row) => row.id !== id
      ? row
      : computeDerived({ ...row, ...changes })));
  }, [readOnly, setRoadRows]);

  const updateRailRow = useCallback((id: string, changes: Partial<RailUserRow>) => {
    if (readOnly) return;
    setRailRows((previousRows) => {
      const calculationChanged =
        Object.prototype.hasOwnProperty.call(changes, "terrain") ||
        Object.prototype.hasOwnProperty.call(changes, "freight");
      const updatedRows = previousRows.map((row) => row.id !== id
        ? row
        : {
          ...row,
          ...changes,
          ...(calculationChanged ? {
            dieselEmissionsIntensity: "",
            dieselEmissions: "",
            dieselEmissionsTotalRefPeriod: "",
          } : {}),
        });
      const updatedRow = updatedRows.find((row) => row.id === id);
      if (!updatedRow) return updatedRows;

      if (calculationChanged) scheduleRailCalculation(updatedRow, updatedRows);
      else scheduleRailSave(updatedRows);
      return updatedRows;
    });
  }, [readOnly, setRailRows, scheduleRailCalculation, scheduleRailSave]);

  return { updateRoadRow, updateRailRow };
}
