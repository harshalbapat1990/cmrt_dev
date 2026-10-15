import { useEffect, type Dispatch, type SetStateAction } from "react";
import ActivityDataService from "@/services/ActivityData.service";
import type { DataEntryRow, StageInstance, StageLabel } from "../dataEntryTypes";

type Params = {
  enabled: boolean;
  projectClass: string | null;
  activeStage: StageLabel;
  activeSubStage: string;
  activeStageInstance: StageInstance | null;
  activeOptionId: string | null;
  apiRowToUiRow: (row: Awaited<ReturnType<typeof ActivityDataService.fetchRows>>[number]) => DataEntryRow;
  updateRows: (key: "concreteRegSimplified" | "concreteRegDetailed", rows: SetStateAction<DataEntryRow[]>) => void;
  recalcAndPersistRows: (key: "concreteRegSimplified" | "concreteRegDetailed", rows: DataEntryRow[], update: Dispatch<SetStateAction<DataEntryRow[]>>) => Promise<void>;
};

/** Loads activity-data-backed concrete tables for the project data-entry page. */
export function useConcreteRegisterRows({
  enabled,
  projectClass,
  activeStage,
  activeSubStage,
  activeStageInstance,
  activeOptionId,
  apiRowToUiRow,
  updateRows,
  recalcAndPersistRows,
}: Params): void {
  useEffect(() => {
    const needsConcrete = enabled && projectClass === "LARGE" &&
      (activeStage === "Design" || activeStage === "Construction") &&
      activeSubStage === "Construction";
    if (!needsConcrete || !activeStageInstance) return;
    if (activeStage === "Design" && activeOptionId === null) return;

    updateRows("concreteRegSimplified", []);
    updateRows("concreteRegDetailed", []);

    let cancelled = false;
    void (async () => {
      try {
        const [rawSimplified, rawDetailed] = await Promise.all([
          ActivityDataService.fetchRows(activeStageInstance.id, "concreteRegSimplified", activeOptionId ?? undefined),
          ActivityDataService.fetchRows(activeStageInstance.id, "concreteRegDetailed", activeOptionId ?? undefined),
        ]);
        if (cancelled) return;
        const simplifiedRows = rawSimplified.map(apiRowToUiRow);
        const detailedRows = rawDetailed.map(apiRowToUiRow);
        updateRows("concreteRegSimplified", simplifiedRows);
        updateRows("concreteRegDetailed", detailedRows);
        if (simplifiedRows.some((row) => row.emissions_tco2e == null)) {
          void recalcAndPersistRows("concreteRegSimplified", simplifiedRows, (rows) => updateRows("concreteRegSimplified", rows));
        }
        if (detailedRows.some((row) => row.emissions_tco2e == null)) {
          void recalcAndPersistRows("concreteRegDetailed", detailedRows, (rows) => updateRows("concreteRegDetailed", rows));
        }
      } catch (error) {
        console.error("Failed to load concrete register:", error);
      }
    })();
    return () => { cancelled = true; };
  }, [enabled, projectClass, activeStage, activeSubStage, activeStageInstance, activeOptionId, apiRowToUiRow, updateRows, recalcAndPersistRows]);
}
