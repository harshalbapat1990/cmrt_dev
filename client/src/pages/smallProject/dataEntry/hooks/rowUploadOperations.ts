import ActivityDataService, { type ActivityDataCreate, type ActivityDataOut } from "@/services/ActivityData.service";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import { fetchAllActiveMrFactors } from "../refurbishmentTableConfig";
import { requireGasesCategoryId } from "../useB1G2Config";
import { isElectricityTable, type UploadKey } from "../stageConstants";
import { resolveTableConfig, normalizeRules } from "../tableConfigRegistry";
import { parseFileToRows } from "../../../../utils/parseFileToRows";
import { validateRows } from "../../../../utils/ValidateRows";
import type { DataEntryRow, StageInstance } from "../dataEntryTypes";
import { toDataEntryRows } from "../dataEntryValidation";

type RowUpdater = (
  key: UploadKey,
  updater: DataEntryRow[] | ((previous: DataEntryRow[]) => DataEntryRow[]),
) => void;

interface Params {
  activeStageInstance: StageInstance | null;
  projectId: string;
  activeOptionId: string | null;
  activePeriod: ConstructionPeriod | null;
  getRows: (key: UploadKey) => DataEntryRow[];
  updateRows: RowUpdater;
  setErrorForKey: (key: UploadKey, error: string | null) => void;
  resolveMetricId: (row: DataEntryRow, tableKey: UploadKey) => Promise<string | null>;
  apiRowToUiRow: (row: ActivityDataOut) => DataEntryRow;
  computeEmissionsForRow: (tableKey: UploadKey, row: DataEntryRow) => Promise<Partial<DataEntryRow> | null>;
  refreshOptionTotals: () => Promise<void>;
  validateComponentReplLife: (tableKey: UploadKey, row: DataEntryRow) => string | null;
}

export function createRowUploadOperations({
  activeStageInstance,
  projectId,
  activeOptionId,
  activePeriod,
  getRows,
  updateRows,
  setErrorForKey,
  resolveMetricId,
  apiRowToUiRow,
  computeEmissionsForRow,
  refreshOptionTotals,
  validateComponentReplLife,
}: Params) {
  const syncComponentUploadToReplacement = async (savedComponents: ActivityDataOut[]) => {
    if (!activeStageInstance || !projectId) return;
    for (const component of savedComponents) {
      if (getRows("componentRepl").some((row) => row._syncedSourceId === component.id)) continue;
      try {
        const extra = component.extra_fields ?? {};
        const extraFields = {
          emissions_category: extra.emissions_category,
          emissions_category_id: extra.emissions_category_id,
          emissions_subcategory: extra.emissions_subcategory,
          emissions_subcategory_id: extra.emissions_subcategory_id,
          emissions_source_name: extra.emissions_source_name,
          emissions_source: extra.emissions_source,
          quantity: component.quantity ?? null,
          life: null,
          _syncedSourceId: component.id,
          _syncedFromConstruction: true,
        };
        const saved = await ActivityDataService.createRow({
          project_id: projectId,
          project_stage_instance_id: activeStageInstance.id,
          project_option_id: activeOptionId ?? null,
          metric_id: component.metric_id ?? null,
          quantity: component.quantity ?? 0,
          unit_id: component.unit_id ?? null,
          emissions_tco2e: null,
          ui_table_key: "componentRepl",
          extra_fields: extraFields,
        });
        updateRows("componentRepl", (rows) => [apiRowToUiRow(saved), ...rows]);
      } catch (error) {
        console.warn("Failed to sync uploaded component → replacement", component.id, error);
      }
    }
  };

  const parseFile = (file: File, tableKey: UploadKey) => {
    const config = resolveTableConfig(tableKey, projectId);
    return parseFileToRows(file, config.fileHeaders ?? [], ["quantity"], {}).then(toDataEntryRows);
  };

  const validateUpload = (parsedRows: DataEntryRow[], tableKey: UploadKey) => {
    const config = resolveTableConfig(tableKey, projectId);
    const rules = normalizeRules(config.rules);
    return validateRows(parsedRows, rules);
  };

  const onUploadSuccess = async (validRows: DataEntryRow[], tableKey: UploadKey) => {
    updateRows(tableKey, validRows);
    if (!activeStageInstance || !projectId) return;

    if (tableKey === "componentRepl") {
      const invalidIndex = validRows.findIndex((row) => validateComponentReplLife("componentRepl", row));
      if (invalidIndex >= 0) {
        const message = validateComponentReplLife("componentRepl", validRows[invalidIndex]);
        setErrorForKey("componentRepl", `Row ${invalidIndex + 1}: ${message}`);
        return;
      }
      setErrorForKey("componentRepl", null);
    }

    try {
      const rowsToSave: DataEntryRow[] = await Promise.all(validRows.map(async (inputRow) => {
        let row: DataEntryRow = { ...inputRow };
        let metricId: string | null = row.metric_id ?? null;
        let quantity = row.quantity;
        let unitId = row.unit_id ?? null;

        if (isElectricityTable(tableKey)) {
          const quantityMwh = row.quantity_mwh;
          quantity = typeof quantityMwh === "number" || typeof quantityMwh === "string" ? quantityMwh : null;
          unitId = null;
          metricId = null;
          row = { ...row, unit_display: row.unit_display ?? "MWh" };
        } else if (tableKey === "useB1G2") {
          unitId = null;
          const gasesCategoryId = await requireGasesCategoryId();
          metricId = await resolveMetricId({ ...row, emissions_category_id: gasesCategoryId }, tableKey);
        } else if (tableKey === "asset") {
          row = {
            ...row,
            mastertype_id: row.mastertype_id ?? null,
            typecast_id: row.mastertype_id ? row.typecast_id : null,
          };
          metricId = await resolveMetricId(row, tableKey);
        } else if (tableKey === "refurbishment") {
          await fetchAllActiveMrFactors();
          metricId = null;
          unitId = null;
        } else {
          metricId = await resolveMetricId(row, tableKey);
        }

        const calcPatch = await computeEmissionsForRow(tableKey, row);
        if (calcPatch) row = { ...row, ...calcPatch };
        if (tableKey === "useB1G2") {
          const charge = Number(row.charge_kg);
          const leakageRate = Number(row.annual_leakage_rate_percent);
          quantity = Number.isFinite(charge) && Number.isFinite(leakageRate) ? charge * leakageRate / 100 : 0;
        }

        const rawEmissions = row.total_emissions_tco2e ?? row.emissions_tco2e;
        const emissions = rawEmissions === "-" || rawEmissions === "" || rawEmissions == null || Number.isNaN(Number(rawEmissions))
          ? null
          : Number(rawEmissions);
        return {
          ...row,
          metric_id: metricId,
          quantity: Number.isFinite(Number(quantity)) ? Number(quantity) : 0,
          unit_id: unitId,
          emissions_tco2e: emissions,
          total_emissions_tco2e: emissions,
        };
      }));

      updateRows(tableKey, rowsToSave);
      const payload: ActivityDataCreate[] = rowsToSave.map((row) => {
        const extraFields: Record<string, unknown> = { ...row };
        delete extraFields._fromApi;
        delete extraFields.id;
        delete extraFields.metric_id;
        delete extraFields.quantity;
        delete extraFields.unit_id;
        return {
          project_id: projectId,
          project_stage_instance_id: activeStageInstance.id,
          project_option_id: activeOptionId ?? null,
          metric_id: row.metric_id ?? null,
          quantity: Number.isFinite(Number(row.quantity)) ? Number(row.quantity) : 0,
          unit_id: row.unit_id ?? null,
          emissions_tco2e: row.emissions_tco2e ?? null,
          total_emissions_tco2e: row.total_emissions_tco2e ?? row.emissions_tco2e ?? null,
          ui_table_key: tableKey,
          extra_fields: extraFields,
          ...(["constructionG2", "constructionG3", "electricity", "opEnergyElectricity", "recurringG3"].includes(tableKey) && activePeriod
            ? { submission_period_id: activePeriod.id }
            : {}),
        };
      });

      if (["constructionG2", "constructionG3"].includes(tableKey) && !activePeriod) {
        throw new Error("No active construction period selected");
      }
      const saved = await ActivityDataService.bulkUpsert(activeStageInstance.id, tableKey, payload);
      if (tableKey === "component") await syncComponentUploadToReplacement(saved);
      updateRows(tableKey, saved.map(apiRowToUiRow));
      setErrorForKey(tableKey, null);
      await refreshOptionTotals();
    } catch (error) {
      console.warn("Bulk upsert failed:", error);
      setErrorForKey(tableKey, "Bulk upload failed. Please check uploaded data.");
    }
  };

  return { parseFile, validateUpload, onUploadSuccess, syncComponentUploadToReplacement };
}
