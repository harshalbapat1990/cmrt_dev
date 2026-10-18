import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import ActivityDataService, { type ActivityDataOut } from "@/services/ActivityData.service";
import type { MeProfile } from "@/context/UserContext";
import { isElectricityTable, type UploadKey } from "./stageConstants";
import { mitigationUiKey, type MitigationSubstitutionLeg } from "./mitigationConstants";
import { requireGasesCategoryId } from "./useB1G2Config";
import { fetchAllActiveMrFactors } from "./refurbishmentTableConfig";
import { validateMitigationElectricityYear } from "./mitigationInlineEditHandlers";
import type { DataEntryRow, StageInstance } from "./dataEntryTypes";

interface MitigationTableUploaderParams {
  projectId: string;
  mitigationStageInstance: StageInstance | null;
  mitigationOptionId: string | null;
  activePeriod: ConstructionPeriod | null;
  user: MeProfile | null;
  operationalLifeYears: number | null;
  mitigationActivityUsesSubmissionPeriod: (tableKey: string) => boolean;
  resolveMetricId: (row: DataEntryRow, tableKey: UploadKey) => Promise<string | null>;
  computeEmissionsForRow: (tableKey: UploadKey, row: DataEntryRow) => Promise<Partial<DataEntryRow> | null>;
  apiRowToUiRow: (row: ActivityDataOut) => DataEntryRow;
  refreshOptionTotals: () => Promise<void>;
  constructionStartDate: string | null;
  constructionEndDate: string | null;
  opsStartYear: number | null;
}

export function createMitigationTableUploader({
  projectId,
  mitigationStageInstance,
  mitigationOptionId,
  activePeriod,
  user,
  operationalLifeYears,
  mitigationActivityUsesSubmissionPeriod,
  resolveMetricId,
  computeEmissionsForRow,
  apiRowToUiRow,
  refreshOptionTotals,
  constructionStartDate,
  constructionEndDate,
  opsStartYear,
}: MitigationTableUploaderParams) {
  return async (
                baseKey: UploadKey,
                projectMitigationId: string,
                validRows: DataEntryRow[],
                substitutionLeg?: MitigationSubstitutionLeg | null,
            ): Promise<{ rows: DataEntryRow[] }> => {
                if (!mitigationStageInstance?.id || !projectId) {
                    throw new Error("Missing mitigation context.");
                }
                const mitKey = mitigationUiKey(baseKey, substitutionLeg ?? undefined);
                const tableKey = baseKey;

                const validateMitigationComponentReplLifeMsg = (row: DataEntryRow): string | null => {
                    const rawLife = row?.life;
                    if (rawLife === undefined || rawLife === null || rawLife === "") return null;
                    const life = Number(rawLife);
                    if (!Number.isFinite(life) || life <= 0) return "Life (years) must be a valid positive number.";
                    const opLife = Number(operationalLifeYears);
                    if (!Number.isFinite(opLife)) return null;
                    if (life >= opLife) return `Life (years) must be less than or equal to the operational life of project (${opLife} years).`;
                    return null;
                };
                const validateMitigationElectricityYearMsg = (row: DataEntryRow): string | null =>
                    validateMitigationElectricityYear(tableKey, row, {
                        constructionStartDate,
                        constructionEndDate,
                        opsStartYear,
                        operationalLifeYears,
                    });

                if (isElectricityTable(tableKey)) {
                    const invalidIndex = validRows.findIndex(
                        (row) => validateMitigationElectricityYearMsg(row) != null,
                    );
                    if (invalidIndex !== -1) {
                        const message =
                            validateMitigationElectricityYearMsg(validRows[invalidIndex]) ??
                            "Invalid row";
                        throw new Error(`Row ${invalidIndex + 1}: ${message}`);
                    }
                }
                if (tableKey === "componentRepl") {
                    const invalidIndex = validRows.findIndex((row) => validateMitigationComponentReplLifeMsg(row) != null);
                    if (invalidIndex !== -1) {
                        const message = validateMitigationComponentReplLifeMsg(validRows[invalidIndex]) ?? "Invalid row";
                        throw new Error(`Row ${invalidIndex + 1}: ${message}`);
                    }
                }
                if (["constructionG2", "constructionG3"].includes(baseKey) && !activePeriod) {
                    throw new Error("No active construction period selected.");
                }
                if (baseKey === "refurbishment") { await fetchAllActiveMrFactors(undefined, projectId); }

                const authorName = [user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.email || "";

                const rowsToSave: DataEntryRow[] = await Promise.all(validRows.map(async (inputRow) => {
                    let row: DataEntryRow = { ...inputRow };
                    let metricId: string | null = row.metric_id ?? null;
                    let quantity = row.quantity;
                    let unit_id = row.unit_id ?? null;
                    if (isElectricityTable(tableKey)) {
                        const quantityMwh = row.quantity_mwh;
                        quantity = typeof quantityMwh === "number" || typeof quantityMwh === "string"
                            ? quantityMwh
                            : null;
                        unit_id = null; metricId = null;
                        row = { ...row, unit_display: "MWh" };
                    } else if (tableKey === "useB1G2") {
                        unit_id = null;
                        const gasesCategoryId = await requireGasesCategoryId();
                        metricId = await resolveMetricId({ ...row, emissions_category_id: gasesCategoryId }, "useB1G2");
                    } else if (tableKey === "asset") {
                        row = { ...row, mastertype_id: row.mastertype_id ?? null, typecast_id: row.mastertype_id ? row.typecast_id : null };
                        metricId = await resolveMetricId(row, tableKey);
                    } else if (tableKey === "refurbishment") {
                        metricId = null; unit_id = null;
                    } else if (tableKey === "concreteRegSimplified") {
                        metricId = null; unit_id = null; const vol = Number(row.volume); quantity = Number.isFinite(vol) ? vol : 0;
                    } else { metricId = await resolveMetricId(row, tableKey); }

                    const computedPatch = await computeEmissionsForRow(tableKey, row);
                    if (computedPatch) { row = { ...row, ...computedPatch }; } else { row = { ...row, emissions_tco2e: null }; }

                    if (tableKey === "useB1G2") {
                        const chargeKg = Number(row.charge_kg); const leakageRate = Number(row.annual_leakage_rate_percent);
                        quantity = Number.isFinite(chargeKg) && Number.isFinite(leakageRate) ? (chargeKg * leakageRate) / 100 : 0;
                    }
                    const rawEmissions = row.total_emissions_tco2e ?? row.emissions_tco2e;
                    const emissionsNum = (rawEmissions === "-" || rawEmissions === "" || rawEmissions == null || Number.isNaN(Number(rawEmissions))) ? null : Number(rawEmissions);
                    if (tableKey === "concreteRegSimplified") {
                        if (typeof computedPatch?._calculation_error === "string") throw new Error(computedPatch._calculation_error);
                        if (emissionsNum === null || !Number.isFinite(emissionsNum)) throw new Error("Unable to calculate emissions for this concrete mix.");
                    }
                    if (row.notes) { row = { ...row, notes_author: authorName, notes_date: new Date().toISOString() }; }
                    return { ...row, metric_id: metricId, quantity: Number.isFinite(Number(quantity)) ? Number(quantity) : 0, unit_id, emissions_tco2e: emissionsNum, total_emissions_tco2e: emissionsNum };
                }));

                const payload = rowsToSave.map((row) => {
                    const extra: Record<string, unknown> = { ...row };
                    delete extra._fromApi;
                    const qRaw = Number(row.quantity ?? row.volume);
                    const quantityNum = Number.isFinite(qRaw) ? qRaw : 0;
                    return {
                        project_id: projectId,
                        project_stage_instance_id: mitigationStageInstance.id,
                        project_option_id: mitigationOptionId ?? undefined,
                        metric_id: row.metric_id ?? undefined,
                        quantity: quantityNum,
                        unit_id: row.unit_id ?? undefined,
                        total_emissions_tco2e: row.total_emissions_tco2e ?? row.emissions_tco2e ?? undefined,
                        ui_table_key: mitKey,
                        extra_fields: extra,
                        project_mitigation_id: projectMitigationId,
                        ...(mitigationActivityUsesSubmissionPeriod(tableKey) ? { submission_period_id: activePeriod!.id } : {}),
                    };
                });

                const savedList = await ActivityDataService.bulkUpsert(mitigationStageInstance.id, mitKey, payload, projectMitigationId);

                const uiRows = Array.isArray(savedList) ? savedList.map((savedRow, i) => {
                    const draftRow = rowsToSave[i];
                    const baseApiRow = apiRowToUiRow(savedRow);
                    if (isElectricityTable(baseKey)) {
                        return { _fromApi: true, ...(savedRow.extra_fields ?? {}), id: savedRow.id, metric_id: savedRow.metric_id, quantity: savedRow.quantity, unit_id: savedRow.unit_id, emissions_tco2e: baseApiRow.emissions_tco2e, location_based_tco2e: savedRow.extra_fields?.location_based_tco2e ?? draftRow.location_based_tco2e ?? null, market_based_tco2e: savedRow.extra_fields?.market_based_tco2e ?? draftRow.market_based_tco2e ?? null };
                    }
                    const rawEm = draftRow.total_emissions_tco2e ?? draftRow.emissions_tco2e;
                    const finalEmissionsNum = (rawEm === "-" || rawEm === "" || rawEm == null || Number.isNaN(Number(rawEm))) ? null : Number(rawEm);
                    const shownEmissions = (finalEmissionsNum != null && !Number.isNaN(Number(finalEmissionsNum))) ? finalEmissionsNum : (baseApiRow.total_emissions_tco2e ?? baseApiRow.emissions_tco2e ?? null);
                    return { ...baseApiRow, emissions_tco2e: shownEmissions, total_emissions_tco2e: shownEmissions };
                }) : [];

                if (baseKey === "component" && Array.isArray(savedList)) {
                    for (let idx = 0; idx < savedList.length; idx++) {
                        const savedComp = savedList[idx];
                        try {
                            const draft = rowsToSave[idx];
                            const quantity = savedComp.quantity;
                            const replExtraFields = { emissions_category: draft.emissions_category, emissions_category_id: draft.emissions_category_id, emissions_subcategory: draft.emissions_subcategory, emissions_subcategory_id: draft.emissions_subcategory_id, source: draft.source, emissions_source: draft.emissions_source, emissions_source_name: draft.emissions_source_name, _syncedSourceId: savedComp.id, _syncedFromConstruction: true, quantity: quantity != null ? Number(quantity) : null };
                            const replDraft = { ...replExtraFields, quantity: quantity ?? 0, unit_id: draft.unit_id ?? null, life: draft.life ?? null };
                            const replPatch = await computeEmissionsForRow("componentRepl", replDraft);
                            const replRaw = replPatch?.total_emissions_tco2e ?? replPatch?.emissions_tco2e;
                            const replEmissionsNum = (replRaw === "-" || replRaw === "" || replRaw == null || Number.isNaN(Number(replRaw))) ? null : Number(replRaw);
                            const finalReplExtraFields: Record<string, unknown> = { ...replExtraFields, ...(replPatch || {}), emissions_tco2e: replEmissionsNum, total_emissions_tco2e: replEmissionsNum };
                            await ActivityDataService.createRow({ project_id: projectId, project_stage_instance_id: mitigationStageInstance.id, project_option_id: mitigationOptionId ?? null, metric_id: savedComp.metric_id ?? null, quantity: quantity != null ? Number(quantity) : 0, unit_id: draft.unit_id ?? null, emissions_tco2e: replEmissionsNum, ui_table_key: mitigationUiKey("componentRepl", substitutionLeg ?? undefined), extra_fields: finalReplExtraFields, project_mitigation_id: projectMitigationId, ...(mitigationActivityUsesSubmissionPeriod("componentRepl") ? { submission_period_id: activePeriod!.id } : {}) });
                        } catch (e) { console.warn("Failed to auto-create mitigation componentRepl row:", e); }
                    }
                }

                await refreshOptionTotals();
                return { rows: uiRows };
            }
}
