import ActivityDataService from "@/services/ActivityData.service";
import type { ActivityDataOut } from "@/services/ActivityData.service";
import type { DataEntryRow } from "../dataEntryTypes";
import { isValidEmission } from "../dataEntryValidation";

interface SaveSimplifiedConcreteMixParams {
  draft: DataEntryRow;
  projectId: string;
  stageInstanceId: string;
  projectOptionId: string | null;
  computeEmissions: (row: DataEntryRow) => Promise<Partial<DataEntryRow> | null>;
  apiRowToUiRow: (row: ActivityDataOut) => DataEntryRow;
  appendRow: (row: DataEntryRow) => void;
  setError: (message: string | null) => void;
  refreshOptionTotals: () => Promise<void>;
}

export async function saveSimplifiedConcreteMixRow({
  draft,
  projectId,
  stageInstanceId,
  projectOptionId,
  computeEmissions,
  apiRowToUiRow,
  appendRow,
  setError,
  refreshOptionTotals,
}: SaveSimplifiedConcreteMixParams): Promise<boolean> {
  try {
    const computedPatch = await computeEmissions(draft);
    const finalDraft = { ...draft, ...(computedPatch ?? {}) };
    if (typeof computedPatch?._calculation_error === "string") {
      setError(computedPatch._calculation_error);
      return false;
    }

    const rawEmissions = computedPatch?.total_emissions_tco2e ?? computedPatch?.emissions_tco2e;
    if (!isValidEmission(rawEmissions)) {
      setError("Unable to calculate emissions for this concrete mix.");
      return false;
    }
    const emissions = rawEmissions === "-" || rawEmissions === "" || rawEmissions == null || Number.isNaN(Number(rawEmissions))
      ? null
      : Number(rawEmissions);
    const extraFields = {
      method: "simplified",
      mixType: finalDraft.mixType ?? null,
      strength: finalDraft.strength ?? null,
      volume: finalDraft.volume != null ? Number(finalDraft.volume) : null,
      targetSCMContent: finalDraft.targetSCMContent != null ? Number(finalDraft.targetSCMContent) : null,
      notes: finalDraft.notes ?? null,
      emissions_tco2e: emissions,
      total_emissions_tco2e: emissions,
    };
    const saved = await ActivityDataService.createRow({
      project_id: projectId,
      project_stage_instance_id: stageInstanceId,
      project_option_id: projectOptionId,
      metric_id: null,
      quantity: finalDraft.volume != null ? Number(finalDraft.volume) : 0,
      unit_id: null,
      emissions_tco2e: emissions,
      ui_table_key: "concreteRegSimplified",
      extra_fields: extraFields,
    });
    appendRow(apiRowToUiRow(saved));
    setError(null);
    await refreshOptionTotals();
    return true;
  } catch (error) {
    console.error("Failed to save simplified concrete mix:", error);
    setError("Failed to save row. Please try again.");
    return false;
  }
}
