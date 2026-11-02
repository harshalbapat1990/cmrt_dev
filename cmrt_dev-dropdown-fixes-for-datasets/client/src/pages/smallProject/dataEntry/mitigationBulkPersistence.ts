import ActivityDataService from "@/services/ActivityData.service";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import type { UploadKey } from "./stageConstants";
import { mitigationUiKey, type MitigationPanelBaseKey, type MitigationSubstitutionLeg, isUsersMitigationBaseKey } from "./mitigationConstants";
import type { DataEntryRow } from "./dataEntryTypes";

interface SaveMitigationBulkTableParams {
  baseKey: MitigationPanelBaseKey;
  projectMitigationId: string;
  rows: DataEntryRow[];
  substitutionLeg?: MitigationSubstitutionLeg | null;
  projectId: string;
  stageInstanceId: string;
  projectOptionId: string | null;
  activePeriod: ConstructionPeriod | null;
  shouldUseSubmissionPeriod: (tableKey: UploadKey) => boolean;
  computeEmissions: (tableKey: UploadKey, row: DataEntryRow) => Promise<Partial<DataEntryRow> | null>;
  refreshOptionTotals: () => Promise<void>;
}

export async function saveMitigationBulkTable({
  baseKey,
  projectMitigationId,
  rows,
  substitutionLeg,
  projectId,
  stageInstanceId,
  projectOptionId,
  activePeriod,
  shouldUseSubmissionPeriod,
  computeEmissions,
  refreshOptionTotals,
}: SaveMitigationBulkTableParams): Promise<void> {
  if (isUsersMitigationBaseKey(baseKey)) return;
  if (["constructionG2", "constructionG3"].includes(baseKey) && !activePeriod) {
    console.warn("Mitigation bulk save skipped (no construction period):", baseKey);
    return;
  }

  const tableKey = baseKey;
  const scopedKey = mitigationUiKey(baseKey, substitutionLeg ?? undefined);
  const rowsToSave = await Promise.all(rows.map(async (row) => {
    const patch = await computeEmissions(tableKey, row);
    return patch ? { ...row, ...patch } : row;
  }));
  const payload = rowsToSave.map((row) => {
    const extraFields: Record<string, unknown> = { ...row };
    delete extraFields._fromApi;
    return {
      project_id: projectId,
      project_stage_instance_id: stageInstanceId,
      project_option_id: projectOptionId ?? undefined,
      metric_id: row.metric_id ?? undefined,
      quantity: Number.isFinite(Number(row.quantity)) ? Number(row.quantity) : 0,
      unit_id: row.unit_id ?? undefined,
      total_emissions_tco2e: row.total_emissions_tco2e ?? row.emissions_tco2e ?? undefined,
      ui_table_key: scopedKey,
      extra_fields: extraFields,
      project_mitigation_id: projectMitigationId,
      ...(shouldUseSubmissionPeriod(tableKey) ? { submission_period_id: activePeriod!.id } : {}),
    };
  });

  await ActivityDataService.bulkUpsert(stageInstanceId, scopedKey, payload, projectMitigationId);
  await refreshOptionTotals();
}
