import { useCallback, useEffect } from "react";
import type { Dispatch, SetStateAction } from "react";
import { computeDerived } from "../roadUserCalculations";
import type { RoadParams, RoadUserYearData } from "../roadUserTypes";
import { emptyRoadUserYear } from "../largeRoadUsersData";

interface Params {
  readOnly: boolean;
  displayedActiveYear: number | null;
  largeUsersYears: number[];
  vehicleTypes: string[];
  globalParams: RoadParams;
  setGlobalParams: Dispatch<SetStateAction<RoadParams>>;
  setYearData: Dispatch<SetStateAction<Record<number, RoadUserYearData>>>;
}

export function useLargeRoadUserEditing({
  readOnly,
  displayedActiveYear,
  largeUsersYears,
  vehicleTypes,
  globalParams,
  setGlobalParams,
  setYearData,
}: Params) {
  const updateRow = useCallback((rowId: string, changes: Partial<RoadUserYearData["rows"][number]>) => {
    if (readOnly || displayedActiveYear === null) return;

    setYearData((previous) => {
      const yearData = previous[displayedActiveYear] ?? {
        ...emptyRoadUserYear(vehicleTypes, globalParams),
      };
      return {
        ...previous,
        [displayedActiveYear]: {
          ...yearData,
          rows: yearData.rows.map((row) => row.id !== rowId
            ? row
            : computeDerived({ ...row, ...changes })),
        },
      };
    });
  }, [readOnly, displayedActiveYear, setYearData, globalParams, vehicleTypes]);

  const updateParams = useCallback((changes: Partial<RoadParams>) => {
    if (readOnly) return;

    const nextParams = { ...globalParams, ...changes };
    setGlobalParams(nextParams);
    setYearData((previousYearData) => {
      const nextYearData: Record<number, RoadUserYearData> = {};
      for (const [year, data] of Object.entries(previousYearData)) {
        nextYearData[Number(year)] = { ...data, params: nextParams };
      }
      return nextYearData;
    });
  }, [readOnly, globalParams, setGlobalParams, setYearData]);

  useEffect(() => {
    if (largeUsersYears.length === 0) return;
    setYearData((previous) => {
      let changed = false;
      const next = { ...previous };
      for (const year of largeUsersYears) {
        if (next[year]) continue;
        next[year] = emptyRoadUserYear(vehicleTypes, globalParams);
        changed = true;
      }
      return changed ? next : previous;
    });
  }, [largeUsersYears, vehicleTypes, globalParams, setYearData]);

  return { updateRow, updateParams };
}
