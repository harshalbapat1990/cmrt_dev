import ActivityDataService from "@/services/ActivityData.service";
import { fetchAllActiveMrFactors } from "../refurbishmentTableConfig";
import { requireGasesCategoryId } from "../useB1G2Config";
import { isElectricityTable, type UploadKey } from "../stageConstants";
import { resolveTableConfig } from "../tableConfigRegistry";
import { isValidEmission } from "../dataEntryValidation";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import type { MeProfile } from "@/context/UserContext";
import type { ActivityDataOut } from "@/services/ActivityData.service";
import type { DataEntryRow, StageInstance } from "../dataEntryTypes";
import { saveSimplifiedConcreteMixRow } from "./saveSimplifiedConcreteMixRow";

interface NewRowSaveParams {
  activeStageInstance: StageInstance | null;
  projectId: string;
  activeOptionId: string | null;
  activePeriod: ConstructionPeriod | null;
  user: MeProfile | null;
  getRows: (key: UploadKey) => DataEntryRow[];
  updateRows: (key: UploadKey, updater: DataEntryRow[] | ((previous: DataEntryRow[]) => DataEntryRow[])) => void;
  setErrorForKey: (key: UploadKey, error: string | null) => void;
  resolveMetricId: (row: DataEntryRow, tableKey: UploadKey) => Promise<string | null>;
  apiRowToUiRow: (row: ActivityDataOut) => DataEntryRow;
  computeEmissionsForRow: (tableKey: UploadKey, row: DataEntryRow) => Promise<Partial<DataEntryRow> | null>;
  refreshOptionTotals: () => Promise<void>;
  validateComponentReplLife: (tableKey: UploadKey, row: DataEntryRow) => string | null;
  validateElectricityYear: (tableKey: UploadKey, row: DataEntryRow) => string | null;
  recalcElectricitySiblings: (tableKey: UploadKey, excludeId: string | null, rows: DataEntryRow[], setRows: React.Dispatch<React.SetStateAction<DataEntryRow[]>>) => Promise<void>;
}

export function createNewRowSaveHandler({
  activeStageInstance,
  projectId,
  activeOptionId,
  activePeriod,
  user,
  getRows,
  updateRows,
  setErrorForKey,
  resolveMetricId,
  apiRowToUiRow,
  computeEmissionsForRow,
  refreshOptionTotals,
  validateComponentReplLife,
  validateElectricityYear,
  recalcElectricitySiblings,
}: NewRowSaveParams) {
  return async (draft: DataEntryRow, tableKey: UploadKey | "users"): Promise<boolean> => {
        if (tableKey === "users") return true;

        if (tableKey === "concreteRegSimplified" && projectId && activeStageInstance) {
            return saveSimplifiedConcreteMixRow({
                draft,
                projectId,
                stageInstanceId: activeStageInstance.id,
                projectOptionId: activeOptionId,
                computeEmissions: (row) => computeEmissionsForRow("concreteRegSimplified", row),
                apiRowToUiRow,
                appendRow: (row) => updateRows("concreteRegSimplified", (previous) => [...previous, row]),
                setError: (error) => setErrorForKey("concreteRegSimplified", error),
                refreshOptionTotals,
            });
        }

        const config = resolveTableConfig(tableKey, projectId);
        const requiredKeys = (config.rules ?? [])
            .filter((rule) => rule.required)
            .map((rule) => rule.key);
        const isMissing = requiredKeys.some(
            (key) => draft[key] === undefined || draft[key] === null || draft[key] === ""
        );
        if (isMissing) {
            setErrorForKey(tableKey, "Please enter required fields");
            return false;
        } else {
            setErrorForKey(tableKey, null);
        }

        if (tableKey === "componentRepl") {
            const lifeError = validateComponentReplLife("componentRepl", draft);
            if (lifeError) { setErrorForKey("componentRepl", lifeError); return false; }
            setErrorForKey("componentRepl", null);
        }

        if (isElectricityTable(tableKey)) {
            const yearError = validateElectricityYear(tableKey, draft);
            if (yearError) { setErrorForKey(tableKey, yearError); return false; }
        }

        if (activeStageInstance && projectId) {
            const existingElectricitySiblings = isElectricityTable(tableKey)
                ? getRows(tableKey).filter((row) => row._fromApi)
                : [];

            try {
                let metricId: string | null = null;
                let extra_fields: Record<string, unknown> = { ...draft };
                let quantity = draft.quantity;
                let unit_id = draft.unit_id ?? null;

                if (isElectricityTable(tableKey)) {
                    const quantityMwh = draft.quantity_mwh;
                    quantity = typeof quantityMwh === "number" || typeof quantityMwh === "string" ? quantityMwh : null;
                    unit_id = null;
                    metricId = null;
                    extra_fields = { ...extra_fields, unit_display: draft.unit_display ?? "MWh" };
                } else if (tableKey === "useB1G2") {
                    unit_id = null;
                    const gasesCategoryId = await requireGasesCategoryId();
                    const metricDraft = { ...draft, emissions_category_id: gasesCategoryId };
                    extra_fields = { ...draft };
                    metricId = await resolveMetricId(metricDraft, "useB1G2");
                } else if (tableKey === "asset") {
                    draft = {
                        ...draft,
                        mastertype_id: draft.mastertype_id ?? null,
                        typecast_id: draft.mastertype_id ? draft.typecast_id : null,
                    };
                    metricId = await resolveMetricId(draft, tableKey);
                } else if (tableKey === "refurbishment") {
                    await fetchAllActiveMrFactors(undefined, projectId);
                    metricId = null;
                    unit_id = null;
                } else {
                    metricId = await resolveMetricId(draft, tableKey);
                }

                let computedPatch: Partial<DataEntryRow> | null = null;
                computedPatch = await computeEmissionsForRow(tableKey, draft);
                if (computedPatch) {
                    draft = { ...draft, ...computedPatch };
                    extra_fields = { ...extra_fields, ...computedPatch };
                } else {
                    draft = { ...draft, emissions_tco2e: null };
                    extra_fields = { ...extra_fields, emissions_tco2e: null };
                }

                if (tableKey === "useB1G2") {
                    const chargeKg = Number(draft.charge_kg);
                    const leakageRate = Number(draft.annual_leakage_rate_percent);
                    quantity =
                        Number.isFinite(chargeKg) && Number.isFinite(leakageRate)
                            ? (chargeKg * leakageRate) / 100
                            : 0;
                }

                const rawEmissions = draft.total_emissions_tco2e ?? draft.emissions_tco2e;
                const finalEmissionsNum =
                    rawEmissions === "-" || rawEmissions === "" || rawEmissions == null || Number.isNaN(Number(rawEmissions))
                        ? null
                        : Number(rawEmissions);
                extra_fields.total_emissions_tco2e = finalEmissionsNum;

                if (extra_fields.notes) {
                    const authorName =
                        [user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.email || "";
                    extra_fields.notes_author = authorName;
                    extra_fields.notes_date = new Date().toISOString();
                }

                const saved = await ActivityDataService.createRow({
                    project_id: projectId,
                    project_stage_instance_id: activeStageInstance.id,
                    project_option_id: activeOptionId ?? null,
                    metric_id: metricId ?? null,
                    quantity: Number.isFinite(Number(quantity)) ? Number(quantity) : 0,
                    unit_id,
                    emissions_tco2e: finalEmissionsNum,
                    ui_table_key: tableKey,
                    extra_fields,
                    ...(["constructionG2", "constructionG3", "electricity", "opEnergyElectricity", "recurringG3"].includes(tableKey) &&
                    activePeriod
                        ? { submission_period_id: activePeriod.id }
                        : {}),
                });
                const baseApiRow = apiRowToUiRow(saved);
                const shownEmissions = isValidEmission(finalEmissionsNum)
                    ? finalEmissionsNum
                    : (baseApiRow.total_emissions_tco2e ?? baseApiRow.emissions_tco2e ?? null);

                const apiRow = isElectricityTable(tableKey)
                    ? {
                          _fromApi: true,
                          ...(saved.extra_fields ?? {}),
                          id: saved.id,
                          metric_id: saved.metric_id,
                          quantity: saved.quantity,
                          unit_id: saved.unit_id,
                          emissions_tco2e: baseApiRow.emissions_tco2e,
                          location_based_tco2e:
                              saved.extra_fields?.location_based_tco2e ??
                              computedPatch?.location_based_tco2e ??
                              draft.location_based_tco2e ??
                              null,
                          market_based_tco2e:
                              saved.extra_fields?.market_based_tco2e ??
                              computedPatch?.market_based_tco2e ??
                              draft.market_based_tco2e ??
                              null,
                      }
                    : {
                          ...baseApiRow,
                          emissions_tco2e: shownEmissions,
                          total_emissions_tco2e: shownEmissions,
                      };

                if (tableKey === "asset") {
                    updateRows("asset", (prev) => [apiRow, ...prev]);
                } else if (tableKey === "component") {
                    updateRows("component", (prev) => [apiRow, ...prev]);
                    try {
                        const replExtraFields = {
                            emissions_category: draft.emissions_category,
                            emissions_category_id: draft.emissions_category_id,
                            emissions_subcategory: draft.emissions_subcategory,
                            emissions_subcategory_id: draft.emissions_subcategory_id,
                            source: draft.source,
                            emissions_source: draft.emissions_source,
                            emissions_source_name: draft.emissions_source_name,
                            _syncedSourceId: saved.id,
                            _syncedFromConstruction: true,
                            quantity: quantity != null ? Number(quantity) : null,
                        };
                        const replDraft = {
                            ...replExtraFields,
                            quantity: quantity ?? 0,
                            unit_id: draft.unit_id ?? null,
                            life: draft.life ?? null,
                        };
                        const replPatch = await computeEmissionsForRow("componentRepl", replDraft);
                        const replRaw = replPatch?.total_emissions_tco2e ?? replPatch?.emissions_tco2e;
                        const replEmissionsNum =
                            replRaw === "-" || replRaw === "" || replRaw == null || Number.isNaN(Number(replRaw))
                                ? null
                                : Number(replRaw);
                        const finalReplExtraFields: Record<string, unknown> = {
                            ...replExtraFields,
                            ...(replPatch || {}),
                            emissions_tco2e: replEmissionsNum,
                            total_emissions_tco2e: replEmissionsNum,
                        };
                        const replSaved = await ActivityDataService.createRow({
                            project_id: projectId,
                            project_stage_instance_id: activeStageInstance.id,
                            project_option_id: activeOptionId ?? null,
                            metric_id: metricId ?? null,
                            quantity: quantity != null ? Number(quantity) : 0,
                            unit_id: draft.unit_id ?? null,
                            emissions_tco2e: replEmissionsNum,
                            ui_table_key: "componentRepl",
                            extra_fields: finalReplExtraFields,
                        });
                        updateRows("componentRepl", (prev) => [apiRowToUiRow(replSaved), ...prev]);
                    } catch (e) {
                        console.warn("Failed to auto-create componentRepl row:", e);
                    }
                } else {
                    updateRows(tableKey, (prev) => [apiRow, ...prev]);
                }

                setErrorForKey(tableKey, null);
                await refreshOptionTotals();
                if (isElectricityTable(tableKey) && existingElectricitySiblings.length > 0) {
                    void recalcElectricitySiblings(
                        tableKey,
                        null,
                        existingElectricitySiblings,
                        (updater) => updateRows(tableKey, updater),
                    );
                }
                return true;
            } catch (e) {
                console.error("Failed to save row:", e);
                setErrorForKey(tableKey, "Failed to save row. Please try again.");
                return false;
            }
        }

        const newRow = { ...draft, id: crypto.randomUUID(), _draft: true };
        updateRows(tableKey, (prev) => [newRow, ...prev]);
        setErrorForKey(tableKey, null);
        return true;
  };
}
