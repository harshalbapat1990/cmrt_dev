import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import ActivityDataService, { type ActivityDataOut } from "@/services/ActivityData.service";
import type { MeProfile } from "@/context/UserContext";
import type { UploadKey } from "./stageConstants";
import { isElectricityTable } from "./stageConstants";
import { resolveTableConfig } from "./tableConfigRegistry";
import { isValidEmission } from "./dataEntryValidation";
import { mitigationUiKey, type MitigationSubstitutionLeg } from "./mitigationConstants";
import { requireGasesCategoryId } from "./useB1G2Config";
import { fetchAllActiveMrFactors } from "./refurbishmentTableConfig";
import { validateMitigationElectricityYear } from "./mitigationInlineEditHandlers";
import type { DataEntryRow, StageInstance } from "./dataEntryTypes";

interface MitigationNewRowSaverParams {
  projectId: string;
  mitigationStageInstance: StageInstance | null;
  mitigationOptionId: string | null;
  activePeriod: ConstructionPeriod | null;
  user: MeProfile | null;
  resolveMetricId: (row: DataEntryRow, tableKey: UploadKey) => Promise<string | null>;
  computeEmissionsForRow: (tableKey: UploadKey, row: DataEntryRow) => Promise<Partial<DataEntryRow> | null>;
  apiRowToUiRow: (row: ActivityDataOut) => DataEntryRow;
  refreshOptionTotals: () => Promise<void>;
  mitigationActivityUsesSubmissionPeriod: (tableKey: string) => boolean;
  constructionStartDate: string | null;
  constructionEndDate: string | null;
  opsStartYear: number | null;
  operationalLifeYears: number | null;
}

export function createMitigationNewRowSaver({
  projectId,
  mitigationStageInstance,
  mitigationOptionId,
  activePeriod,
  user,
  resolveMetricId,
  computeEmissionsForRow,
  apiRowToUiRow,
  refreshOptionTotals,
  mitigationActivityUsesSubmissionPeriod,
  constructionStartDate,
  constructionEndDate,
  opsStartYear,
  operationalLifeYears,
}: MitigationNewRowSaverParams) {
  return async (
    tableKey: UploadKey,
    projectMitigationId: string,
    draft: DataEntryRow,
    appendRow: (tk: UploadKey, row: DataEntryRow) => void,
    setTableError: (msg: string | null) => void,
    substitutionLeg?: MitigationSubstitutionLeg | null,
): Promise<boolean> => {
    if (!mitigationStageInstance?.id || !projectId) return false;

    const config = resolveTableConfig(tableKey, projectId);
    const requiredKeys = (config.rules ?? [])
        .filter((rule) => rule.required)
        .map((rule) => rule.key);
    const isMissing = requiredKeys.some(
        (key) =>
            draft[key] === undefined || draft[key] === null || draft[key] === "",
    );
    if (isMissing) {
        setTableError("Please enter required fields");
        return false;
    }

     if (isElectricityTable(tableKey)) {
        const yearError = validateMitigationElectricityYear(
            tableKey,
            draft,
            {
                constructionStartDate,
                constructionEndDate,
                opsStartYear,
                operationalLifeYears,
            },
        );
        if (yearError) {
            setTableError(yearError);
            return false;
        }
    }

    setTableError(null);

    try {
        let metricId: string | null = null;
        let extra_fields: Record<string, unknown> = { ...draft };
        let quantity = draft.quantity;
        let unit_id = draft.unit_id ?? null;
        const mitKey = mitigationUiKey(tableKey, substitutionLeg ?? undefined);
        if (tableKey === "electricity" || tableKey === "opEnergyElectricity") {
            const quantityMwh = draft.quantity_mwh;
            quantity = typeof quantityMwh === "number" || typeof quantityMwh === "string"
                ? quantityMwh
                : null;
            unit_id = null;
            metricId = null;
            extra_fields = { ...extra_fields, unit_display: "MWh" };
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
        } else if (tableKey === "concreteRegSimplified") {
            metricId = null;
            unit_id = null;
            const vol = Number(draft.volume);
            quantity = Number.isFinite(vol) ? vol : 0;
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
            rawEmissions === "-" ||
            rawEmissions === "" ||
            rawEmissions == null ||
            Number.isNaN(Number(rawEmissions))
                ? null
                : Number(rawEmissions);
        extra_fields.total_emissions_tco2e = finalEmissionsNum;

        if (tableKey === "concreteRegSimplified") {
            if (computedPatch?._calculation_error) {
                setTableError(String(computedPatch._calculation_error));
                return false;
            }
            if (finalEmissionsNum === null || !Number.isFinite(finalEmissionsNum)) {
                setTableError("Unable to calculate emissions for this concrete mix.");
                return false;
            }
        }

        if (extra_fields.notes) {
            const authorName =
                [user?.first_name, user?.last_name].filter(Boolean).join(" ") ||
                user?.email ||
                "";
            extra_fields.notes_author = authorName;
            extra_fields.notes_date = new Date().toISOString();
        }

        const saved = await ActivityDataService.createRow({
            project_id: projectId,
            project_stage_instance_id: mitigationStageInstance.id,
            project_option_id: mitigationOptionId ?? null,
            metric_id: metricId ?? null,
            quantity: Number.isFinite(Number(quantity)) ? Number(quantity) : 0,
            unit_id,
            ui_table_key: mitKey,
            extra_fields,
            project_mitigation_id: projectMitigationId,
            ...(mitigationActivityUsesSubmissionPeriod(tableKey)
                ? { submission_period_id: activePeriod!.id }
                : {}),
        });
        const baseApiRow = apiRowToUiRow(saved);

        const shownEmissions = isValidEmission(finalEmissionsNum)
            ? finalEmissionsNum
            : (baseApiRow.total_emissions_tco2e ?? baseApiRow.emissions_tco2e ?? null);

        const apiRow =
            isElectricityTable(tableKey)
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

        if (tableKey === "component") {
            appendRow("component", apiRow);
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
                const replRaw =
                    replPatch?.total_emissions_tco2e ?? replPatch?.emissions_tco2e;
                const replEmissionsNum =
                    replRaw === "-" ||
                    replRaw === "" ||
                    replRaw == null ||
                    Number.isNaN(Number(replRaw))
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
                    project_stage_instance_id: mitigationStageInstance.id,
                    project_option_id: mitigationOptionId ?? null,
                    metric_id: metricId ?? null,
                    quantity: quantity != null ? Number(quantity) : 0,
                    unit_id: draft.unit_id ?? null,
                    emissions_tco2e: replEmissionsNum,
                    ui_table_key: mitigationUiKey("componentRepl", substitutionLeg ?? undefined),
                    extra_fields: finalReplExtraFields,
                    project_mitigation_id: projectMitigationId,
                    ...(mitigationActivityUsesSubmissionPeriod("componentRepl")
                        ? { submission_period_id: activePeriod!.id }
                        : {}),
                });
                appendRow("componentRepl", apiRowToUiRow(replSaved));
            } catch (e) {
                console.warn("Failed to auto-create mitigation componentRepl row:", e);
            }
        } else {
            appendRow(tableKey, apiRow);
        }

        await refreshOptionTotals();
        return true;
    } catch (e) {
        console.error("Failed to save mitigation row:", e);
        setTableError("Failed to save row. Please try again.");
        return false;
    }
}
}
