import { useCallback, useMemo } from "react";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import {
    type UploadKey,
    isElectricityTable,
    MITIGATION_SUBMISSION_PERIOD_KEYS,
    resolveTableConfig,
} from "./stageConstants";
import { isValidEmission } from "./dataEntryValidation";
import { mitigationUiKey, type MitigationSubstitutionLeg, isUsersMitigationBaseKey } from "./mitigationConstants";
import { GASES_CATEGORY_ID } from "./useB1G2Config";
import { fetchAllActiveMrFactors } from "./refurbishmentTableConfig";
import ActivityDataService from "@/services/ActivityData.service";
import ProjectMitigationsService from "@/services/ProjectMitigations.service";
import {
    createMitigationOnCellChange,
    createMitigationOnRowPatch,
    validateMitigationElectricityYear,
} from "./mitigationInlineEditHandlers";

interface MitigationHandlersParams {
    projectId: string;
    projectClass: string | null;
    activeStage: string;
    activePeriod: ConstructionPeriod | null;
    mitigationStageInstance: any;
    mitigationOptionId: string | null;
    user: any;
    resolveMetricId: (draft: any, tableKey: UploadKey) => Promise<string | null>;
    computeEmissionsForRow: (tableKey: UploadKey, row: any) => Promise<Partial<any> | null>;
    getCalcConfig: (tableKey: UploadKey) => { triggerKeys: string[]; requiredKeys: string[] } | null;
    apiRowToUiRow: (apiRow: any) => any;
    refreshOptionTotals: () => Promise<void>;
    operationalLifeYears: number | null;
    fugitiveList: any[];
    constructionStartDate: string | null;
    constructionEndDate: string | null;
    opsStartYear: number | null;
}

export function useMitigationHandlers({
    projectId,
    projectClass,
    activeStage,
    activePeriod,
    mitigationStageInstance,
    mitigationOptionId,
    user,
    resolveMetricId,
    computeEmissionsForRow,
    getCalcConfig,
    apiRowToUiRow,
    refreshOptionTotals,
    operationalLifeYears,
    fugitiveList,
    constructionStartDate,
    constructionEndDate,
    opsStartYear,
}: MitigationHandlersParams) {
    const mitigationActivityUsesSubmissionPeriod = useCallback(
        (tableKey: string) =>
            activeStage === "Construction" &&
            !!activePeriod &&
            MITIGATION_SUBMISSION_PERIOD_KEYS.includes(tableKey as UploadKey),
        [activeStage, activePeriod],
    );

    const saveMitigationActivityNewRow = useCallback(
        async (
            tableKey: string,
            projectMitigationId: string,
            draft: any,
            appendRow: (tk: string, row: any) => void,
            setTableError: (msg: string | null) => void,
            substitutionLeg?: MitigationSubstitutionLeg | null,
        ): Promise<boolean> => {
            if (!mitigationStageInstance?.id || !projectId) return false;

            const config = resolveTableConfig(tableKey as UploadKey, projectId);
            const requiredKeys = (config.rules || [])
                .filter((rule: any) => rule.required)
                .map((rule: any) => rule.key as string);
            const isMissing = requiredKeys.some(
                (key: any) =>
                    draft[key] === undefined || draft[key] === null || draft[key] === "",
            );
            if (isMissing) {
                setTableError("Please enter required fields");
                return false;
            }

             if (isElectricityTable(tableKey as UploadKey)) {
                const yearError = validateMitigationElectricityYear(
                    tableKey as UploadKey,
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
                let extra_fields: any = { ...draft };
                let quantity = draft.quantity;
                let unit_id = draft.unit_id ?? null;
                const mitKey = mitigationUiKey(tableKey, substitutionLeg ?? undefined);
                if (tableKey === "electricity" || tableKey === "opEnergyElectricity") {
                    quantity = draft.quantity_mwh;
                    unit_id = null;
                    metricId = null;
                    extra_fields = { ...extra_fields, unit_display: "MWh" };
                } else if (tableKey === "useB1G2") {
                    unit_id = null;
                    const metricDraft = { ...draft, emissions_category_id: GASES_CATEGORY_ID };
                    extra_fields = { ...draft };
                    metricId = await resolveMetricId(metricDraft, "useB1G2");
                } else if (tableKey === "asset") {
                    draft = {
                        ...draft,
                        mastertype_id: draft.mastertype_id ?? null,
                        typecast_id: draft.mastertype_id ? draft.typecast_id : null,
                    };
                    metricId = await resolveMetricId(draft, tableKey as UploadKey);
                } else if (tableKey === "refurbishment") {
                    await fetchAllActiveMrFactors();
                    metricId = null;
                    unit_id = null;
                } else if (tableKey === "concreteRegSimplified") {
                    metricId = null;
                    unit_id = null;
                    const vol = Number(draft.volume);
                    quantity = Number.isFinite(vol) ? vol : 0;
                } else {
                    metricId = await resolveMetricId(draft, tableKey as UploadKey);
                }

                let computedPatch: any = null;
                computedPatch = await computeEmissionsForRow(tableKey as UploadKey, draft);
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
                    ...(mitigationActivityUsesSubmissionPeriod(tableKey as UploadKey)
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
                        const finalReplExtraFields: Record<string, any> = {
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
        },
        [
            mitigationStageInstance,
            projectId,
            mitigationOptionId,
            activePeriod,
            activeStage,
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
        ],
    );


const mitigationInlineEditDeps = useMemo(
        () => ({
            computeEmissionsForRow,
            getCalcConfig,
            user,
            fugitiveList,
            operationalLifeYears,
            constructionStartDate,
            constructionEndDate,
            opsStartYear,
        }),
        [
            computeEmissionsForRow,
            getCalcConfig,
            user,
            fugitiveList,
            operationalLifeYears,
            constructionStartDate,
            constructionEndDate,
            opsStartYear,
        ],
    );

    const mitigationElectricityYearDeps = useMemo(
        () => ({
            constructionStartDate,
            constructionEndDate,
            opsStartYear,
            operationalLifeYears,
        }),
        [constructionStartDate, constructionEndDate, opsStartYear, operationalLifeYears],
    );

    const mitigationOnCellChange = useMemo(
        () => createMitigationOnCellChange(mitigationInlineEditDeps),
        [mitigationInlineEditDeps],
    );

    const mitigationOnRowPatch = useMemo(
        () => createMitigationOnRowPatch(mitigationInlineEditDeps),
        [mitigationInlineEditDeps],
    );

    const mitigationPersistence = useMemo(() => {
        if (!mitigationStageInstance?.id || !projectId || projectClass !== "LARGE") return null;

        const periodForFetch = (baseKey: string) =>
            mitigationActivityUsesSubmissionPeriod(baseKey) ? activePeriod!.id : undefined;

        return {
            saveMitigationBulkTable: async (
                baseKey: string,
                projectMitigationId: string,
                rows: any[],
                substitutionLeg?: MitigationSubstitutionLeg | null,
            ) => {
                 if (isUsersMitigationBaseKey(baseKey)) {
                    return;
                }
                const mitKey = mitigationUiKey(baseKey, substitutionLeg ?? undefined);
                const rowsToSave = await Promise.all(
                    rows.map(async (r) => {
                        const calcPatch = await computeEmissionsForRow(baseKey as UploadKey, r);
                        return calcPatch ? { ...r, ...calcPatch } : r;
                    }),
                );
                const payload = rowsToSave.map((row: any) => {
                    const extra: Record<string, any> = { ...row };
                    delete extra._fromApi;
                    return {
                        project_id: projectId,
                        project_stage_instance_id: mitigationStageInstance.id,
                        project_option_id: mitigationOptionId ?? undefined,
                        metric_id: row.metric_id ?? undefined,
                        quantity: row.quantity,
                        unit_id: row.unit_id ?? undefined,
                        total_emissions_tco2e:
                            row.total_emissions_tco2e ?? row.emissions_tco2e ?? undefined,
                        ui_table_key: mitKey,
                        extra_fields: extra,
                        project_mitigation_id: projectMitigationId,
                        ...(mitigationActivityUsesSubmissionPeriod(baseKey as UploadKey)
                            ? { submission_period_id: activePeriod!.id }
                            : {}),
                    };
                });
                if (["constructionG2", "constructionG3"].includes(baseKey) && !activePeriod) {
                    console.warn("Mitigation bulk save skipped (no construction period):", baseKey);
                    return;
                }
                await ActivityDataService.bulkUpsert(
                    mitigationStageInstance.id,
                    mitKey,
                    payload,
                    projectMitigationId,
                );
                await refreshOptionTotals();
            },
            loadMitigationTable: async (
                baseKey: string,
                projectMitigationId: string,
                substitutionLeg?: MitigationSubstitutionLeg | null,
            ) => {
                const mitKey = mitigationUiKey(baseKey, substitutionLeg ?? undefined);
                const raw = await ActivityDataService.fetchRows(
                    mitigationStageInstance.id,
                    mitKey,
                    mitigationOptionId ?? undefined,
                    periodForFetch(baseKey),
                    projectMitigationId,
                );
                return raw.map(apiRowToUiRow);
            },
            patchMitigationMeta: async (
                projectMitigationId: string,
                meta: {
                    name: string;
                    type: string;
                    lifecyclePhase: string;
                    lifecyclePhaseLabel: string;
                    notes?: string;
                    group?: string;
                    submissionStage: string;
                },
            ) => {
                await ProjectMitigationsService.patchMitigation(projectMitigationId, {
                    name: meta.name.trim(),
                    mitigation_type: meta.type || "reduction",
                    lifecycle_phase: meta.lifecyclePhase,
                    lifecycle_phase_label: meta.lifecyclePhaseLabel,
                    notes: meta.notes?.trim() ?? null,
                    group_label: meta.group?.trim() ?? null,
                });
                await refreshOptionTotals();
            },
            createMitigation: async (meta: {
                name: string;
                type: string;
                lifecyclePhase: string;
                lifecyclePhaseLabel: string;
                notes?: string;
                group?: string;
                submissionStage: string;
            }) => {
                const created = await ProjectMitigationsService.create({
                    project_id: projectId,
                    project_stage_instance_id: mitigationStageInstance.id,
                    project_option_id: mitigationOptionId ?? null,
                    submission_stage: meta.submissionStage,
                    name: meta.name.trim(),
                    mitigation_type: meta.type || "reduction",
                    lifecycle_phase: meta.lifecyclePhase,
                    lifecycle_phase_label: meta.lifecyclePhaseLabel,
                    notes: meta.notes?.trim() ?? null,
                    group_label: meta.group?.trim() ?? null,
                });
                await refreshOptionTotals();
                return created.id;
            },
            loadMitigationsForStage: async (submissionStageFilter: string) => {
                const rows = await ProjectMitigationsService.list({
                    project_stage_instance_id: mitigationStageInstance.id,
                    submission_stage: submissionStageFilter,
                });
               /*  const optId = mitigationOptionId ?? null;
                const filtered = rows.filter((r) => {
                    const rid = r.project_option_id ?? null;
                    if (!optId) return true;
                    if (rid == null) return true;
                    return String(rid) === String(optId);
                });
                return filtered.map((r) => ({ */
                return rows.map((r) => ({
                    mitigationId: r.id,
                    name: r.name,
                    type: r.mitigation_type,
                    lifecyclePhase: r.lifecycle_phase,
                    lifecyclePhaseLabel: r.lifecycle_phase_label,
                    notes: r.notes ?? undefined,
                    group: r.group_label ?? undefined,
                    submissionStage: r.submission_stage,
                }));
            },
            deleteMitigation: async (projectMitigationId: string) => {
                await ProjectMitigationsService.remove(projectMitigationId);
                await refreshOptionTotals();
            },
            uploadMitigationTableFile: async (
                baseKey: string,
                projectMitigationId: string,
                validRows: any[],
                substitutionLeg?: MitigationSubstitutionLeg | null,
            ): Promise<{ rows: any[] }> => {
                if (!mitigationStageInstance?.id || !projectId) {
                    throw new Error("Missing mitigation context.");
                }
                const mitKey = mitigationUiKey(baseKey, substitutionLeg ?? undefined);
                const tableKey = baseKey as UploadKey;

                const validateMitigationComponentReplLifeMsg = (row: any): string | null => {
                    const rawLife = row?.life;
                    if (rawLife === undefined || rawLife === null || rawLife === "") return null;
                    const life = Number(rawLife);
                    if (!Number.isFinite(life) || life <= 0) return "Life (years) must be a valid positive number.";
                    const opLife = Number(operationalLifeYears);
                    if (!Number.isFinite(opLife)) return null;
                    if (life >= opLife) return `Life (years) must be less than or equal to the operational life of project (${opLife} years).`;
                    return null;
                };
                const validateMitigationElectricityYearMsg = (row: any): string | null =>
                    validateMitigationElectricityYear(tableKey, row, mitigationElectricityYearDeps);

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
                if (baseKey === "refurbishment") { await fetchAllActiveMrFactors(); }

                const authorName = [user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.email || "";

                const rowsToSave = await Promise.all(validRows.map(async (inputRow) => {
                    let row = { ...inputRow };
                    let metricId: string | null = row.metric_id ?? null;
                    let quantity = row.quantity;
                    let unit_id = row.unit_id ?? null;
                    if (isElectricityTable(tableKey)) {
                        quantity = row.quantity_mwh; unit_id = null; metricId = null;
                        row = { ...row, unit_display: "MWh" };
                    } else if (tableKey === "useB1G2") {
                        unit_id = null;
                        metricId = await resolveMetricId({ ...row, emissions_category_id: GASES_CATEGORY_ID }, "useB1G2");
                    } else if (tableKey === "asset") {
                        row = { ...row, mastertype_id: row.mastertype_id ?? null, typecast_id: row.mastertype_id ? row.typecast_id : null };
                        metricId = await resolveMetricId(row, tableKey);
                    } else if (tableKey === "refurbishment") {
                        metricId = null; unit_id = null;
                    } else if (tableKey === "concreteRegSimplified") {
                        metricId = null; unit_id = null; const vol = Number(row.volume); quantity = Number.isFinite(vol) ? vol : 0;
                    } else { metricId = await resolveMetricId(row, tableKey); }

                    let computedPatch: any = await computeEmissionsForRow(tableKey, row);
                    if (computedPatch) { row = { ...row, ...computedPatch }; } else { row = { ...row, emissions_tco2e: null }; }

                    if (tableKey === "useB1G2") {
                        const chargeKg = Number(row.charge_kg); const leakageRate = Number(row.annual_leakage_rate_percent);
                        quantity = Number.isFinite(chargeKg) && Number.isFinite(leakageRate) ? (chargeKg * leakageRate) / 100 : 0;
                    }
                    const rawEmissions = row.total_emissions_tco2e ?? row.emissions_tco2e;
                    const emissionsNum = (rawEmissions === "-" || rawEmissions === "" || rawEmissions == null || Number.isNaN(Number(rawEmissions))) ? null : Number(rawEmissions);
                    if (tableKey === "concreteRegSimplified") {
                        if (computedPatch?._calculation_error) throw new Error(String(computedPatch._calculation_error));
                        if (emissionsNum === null || !Number.isFinite(emissionsNum)) throw new Error("Unable to calculate emissions for this concrete mix.");
                    }
                    if (row.notes) { row = { ...row, notes_author: authorName, notes_date: new Date().toISOString() }; }
                    return { ...row, metric_id: metricId, quantity: Number.isFinite(Number(quantity)) ? Number(quantity) : 0, unit_id, emissions_tco2e: emissionsNum, total_emissions_tco2e: emissionsNum };
                }));

                const payload = rowsToSave.map((row: any) => {
                    const extra: Record<string, any> = { ...row };
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

                const uiRows = Array.isArray(savedList) ? savedList.map((savedRow: any, i: number) => {
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
                            const finalReplExtraFields: Record<string, any> = { ...replExtraFields, ...(replPatch || {}), emissions_tco2e: replEmissionsNum, total_emissions_tco2e: replEmissionsNum };
                            await ActivityDataService.createRow({ project_id: projectId, project_stage_instance_id: mitigationStageInstance.id, project_option_id: mitigationOptionId ?? null, metric_id: savedComp.metric_id ?? null, quantity: quantity != null ? Number(quantity) : 0, unit_id: draft.unit_id ?? null, emissions_tco2e: replEmissionsNum, ui_table_key: mitigationUiKey("componentRepl", substitutionLeg ?? undefined), extra_fields: finalReplExtraFields, project_mitigation_id: projectMitigationId, ...(mitigationActivityUsesSubmissionPeriod("componentRepl") ? { submission_period_id: activePeriod!.id } : {}) });
                        } catch (e) { console.warn("Failed to auto-create mitigation componentRepl row:", e); }
                    }
                }

                await refreshOptionTotals();
                return { rows: uiRows };
            },
            saveMitigationNewRow: saveMitigationActivityNewRow,
            computeEmissionsForRow: (tableKey: string, row: any) =>
                computeEmissionsForRow(tableKey as UploadKey, row),
            refreshOptionTotals,
            onCellChange: mitigationOnCellChange,
            onRowPatch: mitigationOnRowPatch,
        };
    }, [
        mitigationStageInstance,
        mitigationOptionId,
        projectId,
        projectClass,
        activePeriod,
        activeStage,
        mitigationActivityUsesSubmissionPeriod,
        computeEmissionsForRow,
        apiRowToUiRow,
        refreshOptionTotals,
        saveMitigationActivityNewRow,
        operationalLifeYears,
        mitigationElectricityYearDeps,
        mitigationOnCellChange,
        mitigationOnRowPatch,
    ]);

    return {
        mitigationActivityUsesSubmissionPeriod,
        saveMitigationActivityNewRow,
        mitigationPersistence,
    };
}
