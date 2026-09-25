import React, { useState, useCallback } from "react";
import { NumericInput } from "@/components/common/NumericInput";
import ActivityDataService from "@/services/ActivityData.service";
import { fetchAllActiveMrFactors } from "../refurbishmentTableConfig";
import { GASES_CATEGORY_ID } from "../useB1G2Config";
import {
    type UploadKey,
    isElectricityTable,
    resolveTableConfig,
    normalizeRules,
} from "../stageConstants";
import { hasAllRequired, isValidEmission } from "../dataEntryValidation";
import { buildExtraFields } from "../rowTransforms";
import { parseFileToRows } from "../../../../utils/parseFileToRows";
import { validateRows } from "../../../../utils/ValidateRows";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";

interface UseRowOperationsParams {
    activeStageInstance: any | null;
    projectId: string;
    activeOptionId: string | null;
    activePeriod: ConstructionPeriod | null;
    constructionStartDate: string | null;
    constructionEndDate: string | null;
    opsStartYear: number | null;
    operationalLifeYears: number | null;
    user: any;
    fugitiveList: any[];
    tableRows: any;
    getRows: (key: UploadKey) => any[];
    updateRows: (key: UploadKey, updater: any[] | ((prev: any[]) => any[])) => void;
    setErrorForKey: (key: UploadKey, error: string | null) => void;
    resolveMetricId: (row: any, tableKey: UploadKey) => Promise<string | null>;
    apiRowToUiRow: (row: any) => any;
    computeEmissionsForRow: (tableKey: UploadKey, row: any) => Promise<any>;
    getCalcConfig: (tableKey: UploadKey) => any;
    refreshOptionTotals: () => Promise<void>;
    recalcElectricitySiblings: (
        tableKey: UploadKey | string,
        excludeId: string | null,
        rows: any[],
        setRows: (updater: (prev: any[]) => any[]) => void,
    ) => Promise<void>;
}

export function useRowOperations({
    activeStageInstance,
    projectId,
    activeOptionId,
    activePeriod,
    constructionStartDate,
    constructionEndDate,
    opsStartYear,
    operationalLifeYears,
    user,
    fugitiveList,
    tableRows,
    getRows,
    updateRows,
    setErrorForKey,
    resolveMetricId,
    apiRowToUiRow,
    computeEmissionsForRow,
    getCalcConfig,
    refreshOptionTotals,
    recalcElectricitySiblings,
}: UseRowOperationsParams) {
    const [deleteTarget, setDeleteTarget] = useState<{ id: string; tableKey: UploadKey } | null>(null);
    const [uploadTarget, setUploadTarget] = useState<UploadKey | null>(null);

    const getYearFromValue = (value: any): number | null => {
        if (value == null || value === "") return null;
        if (typeof value === "number") return Number.isFinite(value) ? value : null;
        const str = String(value).trim();
        if (/^\d{4}$/.test(str)) return Number(str);
        const parsed = new Date(str);
        if (!Number.isNaN(parsed.getTime())) return parsed.getFullYear();
        return null;
    };

    const getElectricityYearWindow = useCallback(
        (tableKey: UploadKey): { start: number | null; end: number | null; label: string } => {
            if (tableKey === "electricity") {
                return {
                    start: getYearFromValue(constructionStartDate),
                    end: getYearFromValue(constructionEndDate),
                    label: "construction period",
                };
            }
            if (tableKey === "opEnergyElectricity") {
                const start = getYearFromValue(opsStartYear);
                const end = start && operationalLifeYears ? start + Number(operationalLifeYears) : null;
                return { start, end, label: "operational period" };
            }
            return { start: null, end: null, label: "" };
        },
        [constructionStartDate, constructionEndDate, opsStartYear, operationalLifeYears]
    );

    const validateElectricityYear = useCallback(
        (tableKey: UploadKey, row: any): string | null => {
            if (!isElectricityTable(tableKey)) return null;
            const year = Number(row?.year);
            if (!Number.isFinite(year)) return null;
            const { start, end, label } = getElectricityYearWindow(tableKey);
            if (!start || !end) {
                return tableKey === "electricity"
                    ? "Construction start and end year are required for electricity calculations."
                    : "Operations start year and operational life are required for electricity calculations.";
            }
            if (year < start || year > end) {
                return `Year must be between ${start} and ${end} for the ${label}.`;
            }
            return null;
        },
        [getElectricityYearWindow]
    );

    const validateComponentReplLife = useCallback(
        (tableKey: UploadKey, row: any): string | null => {
            if (tableKey !== "componentRepl") return null;
            const rawLife = row?.life;
            if (rawLife === undefined || rawLife === null || rawLife === "") return null;
            const life = Number(rawLife);
            if (!Number.isFinite(life) || life <= 0) return "Life (years) must be a valid positive number.";
            const opLife = Number(operationalLifeYears);
            if (life > opLife) {
                return `Life (years) must be less than or equal to the operational life of project (${opLife} years).`;
            }
            return null;
        },
        [operationalLifeYears]
    );

    const renderEditor = (col: any, props: any) => {
        if (col.editorType === "year") {
            return (
                <input
                    type="number"
                    className="h-10 w-full bg-white border border-border-input rounded px-2 py-1 text-sm"
                    value={props.value ?? ""}
                    onChange={(e) => props.onChange(e.target.value)}
                    onBlur={() => props.onCommit(props.value)}
                    autoFocus
                    onKeyDown={(e) => {
                        if (e.key === "." || e.key === ",") e.preventDefault();
                    }}
                />
            );
        }
        if (col.editorType === "number") {
            return (
                <NumericInput
                    value={props.value}
                    onChange={props.onChange}
                    onCommit={props.onCommit}
                    allowDecimal
                    autoFocus
                    uncontrolled
                />
            );
        }
        if (col.key === "notes") {
            return (
                <input
                    className="h-10 w-full bg-white border border-border-input rounded px-2 py-1 text-sm"
                    value={props.value}
                    onChange={(e) => props.onChange(e.target.value)}
                    onBlur={() => props.onCommit(props.value)}
                    autoFocus
                />
            );
        }
        return col.renderEditor?.(props);
    };

    const handleSaveBoundaryRow = useCallback(
        async (
            rowId: string,
            tableKey: UploadKey,
            finalRow: any,
            setRows: React.Dispatch<React.SetStateAction<any[]>>
        ) => {
            if (!activeStageInstance || !projectId) return;
            const boundaryId = rowId.replace(/^__BOUNDARY_/, "").replace(/__$/, "");
            try {
                let metricId: string | null = null;
                let unit_id: string | null = finalRow.unit_id ?? null;
                const quantity = finalRow.quantity;

                if (tableKey === "refurbishment") {
                    unit_id = null;
                    await fetchAllActiveMrFactors();
                }

                try { metricId = await resolveMetricId(finalRow, tableKey); } catch { metricId = null; }

                let computedPatch: any = null;
                try { computedPatch = await computeEmissionsForRow(tableKey, finalRow); } catch (e) { console.warn('[useRowOperations] computeEmissionsForRow failed, saving without computed values:', e); }

                const rowToSave = computedPatch ? { ...finalRow, ...computedPatch } : finalRow;
                const rawEmissions = rowToSave.total_emissions_tco2e ?? rowToSave.emissions_tco2e;
                const finalEmissionsNum =
                    rawEmissions == null || rawEmissions === "-" || Number.isNaN(Number(rawEmissions))
                        ? null
                        : Number(rawEmissions);

                const extra_fields: Record<string, any> = {
                    ...rowToSave,
                    reporting_boundary_id: boundaryId,
                    fromBoundary: true,
                    emissions_tco2e: finalEmissionsNum,
                    total_emissions_tco2e: finalEmissionsNum,
                };
                delete extra_fields._fromBoundary;
                delete extra_fields.id;

                const saved = await ActivityDataService.createRow({
                    project_id: projectId,
                    project_stage_instance_id: activeStageInstance.id,
                    project_option_id: activeOptionId ?? null,
                    metric_id: metricId ?? null,
                    quantity: quantity != null ? Number(quantity) : 0,
                    unit_id,
                    emissions_tco2e: finalEmissionsNum,
                    ui_table_key: tableKey,
                    extra_fields,
                    ...(["constructionG2", "constructionG3", "recurringG3"].includes(tableKey) && activePeriod
                        ? { submission_period_id: activePeriod.id }
                        : {}),
                });

                const savedUiRow = apiRowToUiRow(saved);
                setRows((prev) => prev.map((r) => (r.id === rowId ? savedUiRow : r)));

                if (tableKey === "component") {
                    try {
                        const replExtraFields: Record<string, any> = {
                            emissions_category: finalRow.emissions_category,
                            emissions_category_id: finalRow.emissions_category_id,
                            emissions_subcategory: finalRow.emissions_subcategory,
                            emissions_subcategory_id: finalRow.emissions_subcategory_id,
                            source: finalRow.source,
                            emissions_source: finalRow.emissions_source,
                            emissions_source_name: finalRow.emissions_source_name,
                            _syncedSourceId: saved.id,
                            _syncedFromConstruction: true,
                            reporting_boundary_id: boundaryId,
                            fromBoundary: true,
                            quantity: quantity != null ? Number(quantity) : null,
                        };
                        const replDraft = { ...replExtraFields, quantity: quantity ?? 0, unit_id, life: finalRow.life ?? null };
                        let replPatch: any = null;
                        try { replPatch = await computeEmissionsForRow("componentRepl", replDraft); } catch (e) { console.warn('[useRowOperations] replacement emissions computation failed:', e); }
                        const replRaw = replPatch?.total_emissions_tco2e ?? replPatch?.emissions_tco2e;
                        const replEmissionsNum =
                            replRaw === "-" || replRaw === "" || replRaw == null || Number.isNaN(Number(replRaw))
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
                            project_stage_instance_id: activeStageInstance.id,
                            project_option_id: activeOptionId ?? null,
                            metric_id: metricId ?? null,
                            quantity: quantity != null ? Number(quantity) : 0,
                            unit_id,
                            emissions_tco2e: replEmissionsNum,
                            ui_table_key: "componentRepl",
                            extra_fields: finalReplExtraFields,
                        });
                        updateRows("componentRepl", (p: any[]) => [apiRowToUiRow(replSaved), ...p]);
                    } catch (e) {
                        console.warn("Failed to auto-create componentRepl for boundary component row:", e);
                    }
                }
            } catch (e) {
                console.warn("Failed to save boundary row:", tableKey, e);
            }
        },
        [activeStageInstance, projectId, activeOptionId, activePeriod, resolveMetricId, computeEmissionsForRow, apiRowToUiRow, updateRows]
    );

    const syncComponentQtyToReplacement = useCallback(
        async (sourceComponentRowId: string, newQty: any) => {
            const replRow = getRows("componentRepl").find((r: any) => r._syncedSourceId === sourceComponentRowId);
            if (!replRow?._fromApi) return;

            const draft = { ...replRow, quantity: newQty };
            const patch = await computeEmissionsForRow("componentRepl", draft);
            const final = patch ? { ...draft, ...patch } : draft;

            updateRows("componentRepl", (prev: any[]) => prev.map((r) => (r.id === replRow.id ? final : r)));

            const raw = final.total_emissions_tco2e ?? final.emissions_tco2e;
            const emissionsNum =
                raw === "-" || raw === "" || raw == null || Number.isNaN(Number(raw)) ? null : Number(raw);

            await ActivityDataService.updateRow(replRow.id, {
                quantity: Number(newQty),
                emissions_tco2e: emissionsNum,
                extra_fields: buildExtraFields(final, { keepEmissions: true, tableKey: "componentRepl" }),
            });
            await refreshOptionTotals();
        },
        [tableRows, computeEmissionsForRow, getRows, updateRows, refreshOptionTotals]
    );

    const onCellChange =
        (tableKey: UploadKey, setRows: React.Dispatch<React.SetStateAction<any[]>>) =>
        async ({ id, key, value, item }: any) => {
            let finalRow = { ...item, [key]: value };
            const cfg = getCalcConfig(tableKey);

            if (isElectricityTable(tableKey)) {
                const electricityTriggerKeys = new Set(["emission_source", "year", "quantity_mwh"]);
                if (electricityTriggerKeys.has(String(key))) {
                    const updatedRow = { ...item, [key]: value };
                    const yearError = validateElectricityYear(tableKey, updatedRow);
                    if (yearError) {
                        setErrorForKey(tableKey, yearError);
                        setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...updatedRow } : r)));
                        return;
                    }
                    setErrorForKey(tableKey, null);
                    if (updatedRow.emission_source && updatedRow.year && updatedRow.quantity_mwh) {
                        const calc = await computeEmissionsForRow(tableKey, updatedRow);
                        if (!calc) return;
                        const nextRow = {
                            ...updatedRow,
                            ...calc,
                            location_based_tco2e: calc.location_based_tco2e ?? null,
                            market_based_tco2e: calc.market_based_tco2e ?? null,
                            unit_display: updatedRow.unit_display ?? "MWh",
                        };
                        setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...nextRow } : r)));
                        if (item?._fromApi) {
                            const raw = nextRow.total_emissions_tco2e ?? nextRow.emissions_tco2e;
                            const emissionsNum =
                                raw === "-" || raw === "" || raw == null || Number.isNaN(Number(raw)) ? null : Number(raw);
                            const extra_fields = {
                                ...nextRow,
                                location_based_tco2e: nextRow.location_based_tco2e,
                                market_based_tco2e: nextRow.market_based_tco2e,
                                unit_display: updatedRow.unit_display ?? "MWh",
                            };
                            delete extra_fields._fromApi;
                            await ActivityDataService.updateRow(id, {
                                quantity: Number(nextRow.quantity_mwh),
                                emissions_tco2e: emissionsNum,
                                extra_fields,
                            });
                            void recalcElectricitySiblings(
                                tableKey,
                                id,
                                getRows(tableKey),
                                (updater) => updateRows(tableKey, updater),
                            );
                        }
                    }
                } else {
                    setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));
                    if (item?._fromApi) {
                        const extra_fields = { ...item, [key]: value };
                        delete extra_fields._fromApi;
                        await ActivityDataService.updateRow(id, { extra_fields });
                        await refreshOptionTotals();
                    }
                }
                return;
            }

            if (tableKey === "useB1G2" && String(key) === "application_type_id") {
                const eq = fugitiveList.find((e: any) => e.id === value);
                setRows((prev) =>
                    prev.map((row) =>
                        row.id === id
                            ? {
                                  ...row,
                                  application_type_id: value,
                                  application_type: eq?.equipment_type ?? "",
                                  annual_leakage_rate_percent: eq
                                      ? parseFloat(eq.default_annual_leakage_rate)
                                      : null,
                              }
                            : row
                    )
                );
                if (item?._fromApi) {
                    const extra_fields = {
                        ...item,
                        application_type_id: value,
                        application_type: eq?.equipment_type ?? "",
                        annual_leakage_rate_percent: eq ? parseFloat(eq.default_annual_leakage_rate) : null,
                    };
                    delete extra_fields._fromApi;
                    await ActivityDataService.updateRow(id, { extra_fields });
                }
                return;
            }

            if (tableKey === "componentRepl") {
                const isComponentReplTrigger = cfg?.triggerKeys?.includes(String(key));
                if (isComponentReplTrigger) {
                    const lifeError = validateComponentReplLife(tableKey, finalRow);
                    if (lifeError) {
                        setErrorForKey("componentRepl", lifeError);
                        setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));
                        return;
                    }
                    setErrorForKey("componentRepl", null);
                }
            }

            const isTrigger = !!cfg && cfg.triggerKeys.includes(String(key));

            if (isTrigger) {
                if (tableKey === "refurbishment") await fetchAllActiveMrFactors();

                const calcPatch = await computeEmissionsForRow(tableKey, finalRow);

                if (calcPatch) {
                    const requiredPresent = cfg ? hasAllRequired(finalRow, cfg.requiredKeys) : false;
                    const nextVal = calcPatch.total_emissions_tco2e ?? calcPatch.emissions_tco2e;
                    const calcFailedButShouldHaveWorked = requiredPresent && !isValidEmission(nextVal);
                    if (!calcFailedButShouldHaveWorked) {
                        finalRow = { ...finalRow, ...calcPatch };
                    }
                }

                setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));

                if (item?._fromApi) {
                    const apiPatch: any = {
                        ...(finalRow.quantity != null ? { quantity: Number(finalRow.quantity) } : {}),
                        ...(finalRow.unit_id != null ? { unit_id: finalRow.unit_id } : {}),
                        extra_fields: buildExtraFields(finalRow, { keepEmissions: true, tableKey }),
                    };
                    await ActivityDataService.updateRow(id, apiPatch);
                    await refreshOptionTotals();
                }

                if (tableKey === "component" && String(key) === "quantity" && item?._fromApi) {
                    await syncComponentQtyToReplacement(id, value);
                }

                if (item?._fromBoundary && String(id).startsWith("__BOUNDARY_") && finalRow.quantity != null) {
                    await handleSaveBoundaryRow(String(id), tableKey, finalRow, setRows);
                }

                return;
            }

            if (String(key) === "notes") {
                const authorName =
                    [user?.first_name, user?.last_name].filter(Boolean).join(" ") ||
                    user?.email ||
                    "";
                if (value) {
                    finalRow = { ...finalRow, notes_author: authorName, notes_date: new Date().toISOString() };
                } else {
                    finalRow = { ...finalRow, notes_author: null, notes_date: null };
                }
            }

            setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));

            if (item?._fromApi) {
                const topLevelKeys = new Set(["quantity", "unit_id", "metric_id"]);
                const shouldSave = topLevelKeys.has(String(key)) || key === "life" || key === "notes";
                if (shouldSave) {
                    const patch: any = {};
                    if (topLevelKeys.has(String(key))) {
                        patch[key] = value;
                    } else {
                        const extra_fields = { ...finalRow };
                        delete extra_fields._fromApi;
                        patch.extra_fields = extra_fields;
                    }
                    await ActivityDataService.updateRow(id, patch);
                }
            }
        };

    const onRowPatch =
        (_tableKey: UploadKey, setRows: React.Dispatch<React.SetStateAction<any[]>>) =>
        async ({ id, patch, item }: any) => {
            if (_tableKey === "concreteRegSimplified" || _tableKey === "concreteRegDetailed") {
                let finalRow = { ...item, ...patch };
                try {
                    const calcPatch = await computeEmissionsForRow(_tableKey, finalRow);
                    if (calcPatch) finalRow = { ...finalRow, ...calcPatch };
                    setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));
                    const rawEmissions = finalRow.total_emissions_tco2e ?? finalRow.emissions_tco2e;
                    const emissionsNum =
                        rawEmissions === "-" || rawEmissions === "" || rawEmissions == null || Number.isNaN(Number(rawEmissions))
                            ? null
                            : Number(rawEmissions);
                    const extraFields = { ...finalRow };
                    delete extraFields._fromApi;
                    delete extraFields.id;
                    delete extraFields.metric_id;
                    delete extraFields.unit_id;
                    extraFields.emissions_tco2e = emissionsNum;
                    extraFields.total_emissions_tco2e = emissionsNum;
                    const quantity = _tableKey === "concreteRegSimplified"
                        ? (finalRow.volume != null ? Number(finalRow.volume) : 0)
                        : (finalRow.quantity != null ? Number(finalRow.quantity) : 0);
                    await ActivityDataService.updateRow(id, {
                        quantity,
                        emissions_tco2e: emissionsNum,
                        extra_fields: extraFields,
                    });
                    await refreshOptionTotals();
                } catch (e) {
                    console.error("Failed to patch concrete register row:", e);
                }
                return;
            }

            let finalRow = { ...item, ...patch };
            setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));

            if (isElectricityTable(_tableKey)) {
                const yearError = validateElectricityYear(_tableKey, finalRow);
                if (yearError) { setErrorForKey(_tableKey, yearError); return; }
                setErrorForKey(_tableKey, null);
            }

            const cfg = getCalcConfig(_tableKey);
            const touchedTrigger = cfg?.triggerKeys?.some((k: string) =>
                Object.prototype.hasOwnProperty.call(patch, k)
            );

            if (_tableKey === "componentRepl" && touchedTrigger) {
                const lifeError = validateComponentReplLife(_tableKey, finalRow);
                if (lifeError) { setErrorForKey("componentRepl", lifeError); return; }
                setErrorForKey("componentRepl", null);
            }

            let didUpdate = false;

            if (cfg && touchedTrigger) {
                const calcPatch = await computeEmissionsForRow(_tableKey, finalRow);

                if (calcPatch) {
                    finalRow = { ...finalRow, ...calcPatch };
                    setRows((prev) => prev.map((r) => (r.id === id ? finalRow : r)));

                    if (isElectricityTable(_tableKey) && item?._fromApi && calcPatch) {
                        const raw = calcPatch.total_emissions_tco2e ?? calcPatch.emissions_tco2e;
                        const emissionsNum =
                            raw === "-" || raw == null || Number.isNaN(Number(raw)) ? null : Number(raw);
                        const extraFields = {
                            ...(item.extra_fields ?? item),
                            ...finalRow,
                            ...calcPatch,
                            unit_display: finalRow.unit_display ?? "MWh",
                        };
                        delete extraFields._fromApi;
                        await ActivityDataService.updateRow(id, {
                            quantity: Number(finalRow.quantity_mwh),
                            emissions_tco2e: emissionsNum,
                            extra_fields: extraFields,
                        });
                        didUpdate = true;
                        void recalcElectricitySiblings(
                            _tableKey,
                            id,
                            getRows(_tableKey),
                            (updater) => updateRows(_tableKey, updater),
                        );
                    }
                }

                const topLevelKeys = new Set(["quantity", "unit_id"]);
                const hasSaveable = Object.keys(patch).some(
                    (k) => topLevelKeys.has(k) || k === "life" || k === "notes"
                );

                if (hasSaveable && item?._fromApi) {
                    try {
                        const apiPatch: any = {};
                        for (const [k, v] of Object.entries(patch)) {
                            if (topLevelKeys.has(k)) apiPatch[k] = v;
                        }
                        apiPatch.extra_fields = buildExtraFields(finalRow, { keepEmissions: true, tableKey: _tableKey });
                        await ActivityDataService.updateRow(id, apiPatch);
                        didUpdate = true;
                    } catch (e) {
                        console.warn("Failed to patch row:", e);
                    }
                }

                if (!didUpdate && item?._fromApi) {
                    try {
                        const apiPatch: any = {
                            ...(finalRow.quantity != null ? { quantity: Number(finalRow.quantity) } : {}),
                            extra_fields: buildExtraFields(finalRow, { keepEmissions: true, tableKey: _tableKey }),
                        };
                        await ActivityDataService.updateRow(id, apiPatch);
                        didUpdate = true;
                    } catch (e) {
                        console.warn("Failed to persist select-triggered emission update:", e);
                    }
                }

                if (didUpdate) await refreshOptionTotals();

                if (_tableKey === "component" && "quantity" in patch && item?._fromApi) {
                    const replRow = getRows("componentRepl").find((r: any) => r._syncedSourceId === id);
                    if (replRow?._fromApi) {
                        try {
                            const replDraft = { ...replRow, quantity: (patch as any).quantity };
                            const replPatch = await computeEmissionsForRow("componentRepl", replDraft);
                            const finalReplRow = { ...replDraft, ...(replPatch || {}) };
                            const raw = finalReplRow.total_emissions_tco2e ?? finalReplRow.emissions_tco2e;
                            const replEmissionsNum =
                                raw === "-" || raw == null || Number.isNaN(Number(raw)) ? null : Number(raw);
                            await ActivityDataService.updateRow(replRow.id, {
                                quantity: (patch as any).quantity,
                                emissions_tco2e: replEmissionsNum,
                                extra_fields: (() => {
                                    const ef = { ...finalReplRow };
                                    delete ef._fromApi;
                                    delete ef.id;
                                    delete ef.metric_id;
                                    delete ef.quantity;
                                    delete ef.unit_id;
                                    delete ef.emissions_tco2e;
                                    delete ef.total_emissions_tco2e;
                                    return ef;
                                })(),
                            });
                            updateRows("componentRepl", (prev: any[]) =>
                                prev.map((r) => (r.id === replRow.id ? finalReplRow : r))
                            );
                        } catch (e) {
                            console.warn("Failed to sync quantity to componentRepl:", e);
                        }
                    }
                }
            }
        };

    const doDeleteRow = useCallback(async () => {
        if (!deleteTarget) return;
        if (deleteTarget.tableKey === "concreteRegSimplified" || deleteTarget.tableKey === "concreteRegDetailed") {
            try {
                await ActivityDataService.deleteRow(deleteTarget.id);
            } catch (e) {
                console.error("Failed to delete concrete mix:", e);
            }
            updateRows(deleteTarget.tableKey, (prev: any[]) => prev.filter((r: any) => r.id !== deleteTarget.id));
            setDeleteTarget(null);
            return;
        }
        if (deleteTarget.tableKey === "component") {
            const replRow = getRows("componentRepl").find((r: any) => r._syncedSourceId === deleteTarget.id);
            if (replRow?._fromApi) {
                try {
                    await ActivityDataService.deleteRow(replRow.id);
                    updateRows("componentRepl", (prev: any[]) => prev.filter((r: any) => r.id !== replRow.id));
                } catch (e) {
                    console.warn("Failed to delete synced componentRepl row:", e);
                }
            }
        }
        const electricitySiblings = isElectricityTable(deleteTarget.tableKey)
            ? getRows(deleteTarget.tableKey).filter(
                  (r: any) => r.id !== deleteTarget.id && r._fromApi,
              )
            : [];
        await ActivityDataService.deleteRow(deleteTarget.id);
        await refreshOptionTotals();
        updateRows(deleteTarget.tableKey, (prev: any[]) => prev.filter((r: any) => r.id !== deleteTarget.id));
        setDeleteTarget(null);
        if (electricitySiblings.length > 0) {
            void recalcElectricitySiblings(
                deleteTarget.tableKey,
                null,
                electricitySiblings,
                (updater) => updateRows(deleteTarget.tableKey, updater),
            );
        }
    }, [deleteTarget, tableRows, updateRows, getRows, refreshOptionTotals, recalcElectricitySiblings]);

    const syncComponentUploadToReplacement = async (savedComponents: any[]) => {
        if (!activeStageInstance || !projectId) return;
        for (const comp of savedComponents) {
            const alreadyExists = getRows("componentRepl").some(
                (r: any) => r._syncedSourceId === comp.id
            );
            if (alreadyExists) continue;
            try {
                const extra = comp.extra_fields ?? {};
                const replExtraFields = {
                    emissions_category: extra.emissions_category,
                    emissions_category_id: extra.emissions_category_id,
                    emissions_subcategory: extra.emissions_subcategory,
                    emissions_subcategory_id: extra.emissions_subcategory_id,
                    emissions_source_name: extra.emissions_source_name,
                    emissions_source: extra.emissions_source,
                    quantity: comp.quantity ?? null,
                    life: null,
                    _syncedSourceId: comp.id,
                    _syncedFromConstruction: true,
                };
                const replSaved = await ActivityDataService.createRow({
                    project_id: projectId,
                    project_stage_instance_id: activeStageInstance.id,
                    project_option_id: activeOptionId ?? null,
                    metric_id: comp.metric_id ?? null,
                    quantity: comp.quantity ?? 0,
                    unit_id: comp.unit_id ?? null,
                    emissions_tco2e: null,
                    ui_table_key: "componentRepl",
                    extra_fields: replExtraFields,
                });
                updateRows("componentRepl", (prev: any[]) => [apiRowToUiRow(replSaved), ...prev]);
            } catch (e) {
                console.warn("Failed to sync uploaded component → replacement", comp.id, e);
            }
        }
    };

    const parseFile = (file: File, tableKey: UploadKey) => {
        const config = resolveTableConfig(tableKey, projectId);
        return parseFileToRows(file, config.fileHeaders, ["quantity"], {});
    };

    const validateUpload = (parsedRows: any[], tableKey: UploadKey) => {
        const config = resolveTableConfig(tableKey, projectId);
        const rules = normalizeRules(config.rules);
        return validateRows(parsedRows, rules as any);
    };

    const onUploadSuccess = async (validRows: any[], tableKey: UploadKey) => {
        updateRows(tableKey, validRows);
        if (!activeStageInstance || !projectId) return;

        if (tableKey === "componentRepl") {
            const invalidIndex = validRows.findIndex((row) => validateComponentReplLife("componentRepl", row));
            if (invalidIndex !== -1) {
                const message = validateComponentReplLife("componentRepl", validRows[invalidIndex]);
                setErrorForKey("componentRepl", `Row ${invalidIndex + 1}: ${message}`);
                return;
            }
            setErrorForKey("componentRepl", null);
        }

        try {
            const rowsToSave = await Promise.all(
                validRows.map(async (inputRow) => {
                    let row = { ...inputRow };
                    let metricId: string | null = row.metric_id ?? null;
                    let quantity = row.quantity;
                    let unit_id = row.unit_id ?? null;

                    if (isElectricityTable(tableKey)) {
                        quantity = row.quantity_mwh;
                        unit_id = null;
                        metricId = null;
                        row = { ...row, unit_display: row.unit_display ?? "MWh" };
                    } else if (tableKey === "useB1G2") {
                        unit_id = null;
                        const metricDraft = { ...row, emissions_category_id: GASES_CATEGORY_ID };
                        metricId = await resolveMetricId(metricDraft, "useB1G2");
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
                        unit_id = null;
                    } else {
                        metricId = await resolveMetricId(row, tableKey);
                    }

                    const calcPatch = await computeEmissionsForRow(tableKey, row);
                    if (calcPatch) row = { ...row, ...calcPatch };

                    if (tableKey === "useB1G2") {
                        const chargeKg = Number(row.charge_kg);
                        const leakageRate = Number(row.annual_leakage_rate_percent);
                        quantity =
                            Number.isFinite(chargeKg) && Number.isFinite(leakageRate)
                                ? (chargeKg * leakageRate) / 100
                                : 0;
                    }

                    const rawEmissions = row.total_emissions_tco2e ?? row.emissions_tco2e;
                    const emissionsNum =
                        rawEmissions === "-" || rawEmissions === "" || rawEmissions == null || Number.isNaN(Number(rawEmissions))
                            ? null
                            : Number(rawEmissions);

                    return {
                        ...row,
                        metric_id: metricId,
                        quantity: Number.isFinite(Number(quantity)) ? Number(quantity) : 0,
                        unit_id,
                        emissions_tco2e: emissionsNum,
                        total_emissions_tco2e: emissionsNum,
                    };
                })
            );

            updateRows(tableKey, rowsToSave);

            const payload = rowsToSave.map((row: any) => {
                const extra_fields = { ...row };
                delete extra_fields._fromApi;
                delete extra_fields.id;
                delete extra_fields.metric_id;
                delete extra_fields.quantity;
                delete extra_fields.unit_id;
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
                    extra_fields,
                    ...(["constructionG2", "constructionG3", "electricity", "opEnergyElectricity", "recurringG3"].includes(tableKey) &&
                    activePeriod
                        ? { submission_period_id: activePeriod.id }
                        : {}),
                };
            });

            if (["constructionG2", "constructionG3"].includes(tableKey) && !activePeriod) {
                throw new Error("No active construction period selected");
            }

            const saved = await ActivityDataService.bulkUpsert(activeStageInstance.id, tableKey, payload);

            if (tableKey === "component" && Array.isArray(saved)) {
                await syncComponentUploadToReplacement(saved);
            }

            if (Array.isArray(saved)) {
                updateRows(tableKey, saved.map(apiRowToUiRow));
            }

            setErrorForKey(tableKey, null);
            await refreshOptionTotals();
        } catch (e) {
            console.warn("Bulk upsert failed:", e);
            setErrorForKey(tableKey, "Bulk upload failed. Please check uploaded data.");
        }
    };

    const handleSaveNewRow = async (draft: any, tableKey: string) => {
        if (tableKey === "users") return true;

        if (tableKey === "concreteRegSimplified" && projectId && activeStageInstance) {
            try {
                const computedPatch = await computeEmissionsForRow("concreteRegSimplified", draft);
                const finalDraft = { ...draft, ...(computedPatch || {}) };
                if (computedPatch?._calculation_error) {
                    setErrorForKey("concreteRegSimplified", computedPatch._calculation_error);
                    return false;
                }
                const rawEmissions = computedPatch?.total_emissions_tco2e ?? computedPatch?.emissions_tco2e;
                if (!isValidEmission(rawEmissions)) {
                    setErrorForKey("concreteRegSimplified", "Unable to calculate emissions for this concrete mix.");
                    return false;
                }
                const emissionsNum =
                    rawEmissions === "-" || rawEmissions === "" || rawEmissions == null || Number.isNaN(Number(rawEmissions))
                        ? null
                        : Number(rawEmissions);
                const extra_fields = {
                    method: "simplified",
                    mixType: finalDraft.mixType ?? null,
                    strength: finalDraft.strength ?? null,
                    volume: finalDraft.volume != null ? Number(finalDraft.volume) : null,
                    targetSCMContent: finalDraft.targetSCMContent != null ? Number(finalDraft.targetSCMContent) : null,
                    notes: finalDraft.notes ?? null,
                    emissions_tco2e: emissionsNum,
                    total_emissions_tco2e: emissionsNum,
                };
                const saved = await ActivityDataService.createRow({
                    project_id: projectId,
                    project_stage_instance_id: activeStageInstance.id,
                    project_option_id: activeOptionId ?? null,
                    metric_id: null,
                    quantity: finalDraft.volume != null ? Number(finalDraft.volume) : 0,
                    unit_id: null,
                    emissions_tco2e: emissionsNum,
                    ui_table_key: "concreteRegSimplified",
                    extra_fields,
                });
                const newRow = apiRowToUiRow(saved);
                updateRows("concreteRegSimplified", (prev: any[]) => [...prev, newRow]);
                setErrorForKey("concreteRegSimplified", null);
                await refreshOptionTotals();
                return true;
            } catch (e) {
                console.error("Failed to save simplified concrete mix:", e);
                setErrorForKey("concreteRegSimplified", "Failed to save row. Please try again.");
                return false;
            }
        }

        const config = resolveTableConfig(tableKey as UploadKey, projectId);
        const requiredKeys = (config.rules || [])
            .filter((rule: any) => rule.required)
            .map((rule: any) => rule.key as string);
        const isMissing = requiredKeys.some(
            (key: string) => draft[key] === undefined || draft[key] === null || draft[key] === ""
        );
        if (isMissing) {
            setErrorForKey(tableKey as UploadKey, "Please enter required fields");
            return false;
        } else {
            setErrorForKey(tableKey as UploadKey, null);
        }

        if (tableKey === "componentRepl") {
            const lifeError = validateComponentReplLife("componentRepl", draft);
            if (lifeError) { setErrorForKey("componentRepl", lifeError); return false; }
            setErrorForKey("componentRepl", null);
        }

        if (isElectricityTable(tableKey as UploadKey)) {
            const yearError = validateElectricityYear(tableKey as UploadKey, draft);
            if (yearError) { setErrorForKey(tableKey as UploadKey, yearError); return false; }
        }

        if (activeStageInstance && projectId) {
            const existingElectricitySiblings = isElectricityTable(tableKey)
                ? getRows(tableKey as UploadKey).filter((r: any) => r._fromApi)
                : [];

            try {
                let metricId: string | null = null;
                let extra_fields: any = { ...draft };
                let quantity = draft.quantity;
                let unit_id = draft.unit_id ?? null;

                if (isElectricityTable(tableKey)) {
                    quantity = draft.quantity_mwh;
                    unit_id = null;
                    metricId = null;
                    extra_fields = { ...extra_fields, unit_display: draft.unit_display ?? "MWh" };
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
                    updateRows("asset", (p: any[]) => [apiRow, ...p]);
                } else if (tableKey === "component") {
                    updateRows("component", (p: any[]) => [apiRow, ...p]);
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
                        const finalReplExtraFields: Record<string, any> = {
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
                        updateRows("componentRepl", (p: any[]) => [apiRowToUiRow(replSaved), ...p]);
                    } catch (e) {
                        console.warn("Failed to auto-create componentRepl row:", e);
                    }
                } else {
                    updateRows(tableKey as UploadKey, (p: any[]) => [apiRow, ...p]);
                }

                setErrorForKey(tableKey as UploadKey, null);
                await refreshOptionTotals();
                if (isElectricityTable(tableKey) && existingElectricitySiblings.length > 0) {
                    void recalcElectricitySiblings(
                        tableKey,
                        null,
                        existingElectricitySiblings,
                        (updater) => updateRows(tableKey as UploadKey, updater),
                    );
                }
                return true;
            } catch (e) {
                console.error("Failed to save row:", e);
                setErrorForKey(tableKey as UploadKey, "Failed to save row. Please try again.");
                return false;
            }
        }

        const newRow = { ...draft, id: crypto.randomUUID(), _draft: true };
        updateRows(tableKey as UploadKey, (p: any[]) => [newRow, ...p]);
        setErrorForKey(tableKey as UploadKey, null);
        return true;
    };

    return {
        deleteTarget,
        setDeleteTarget,
        uploadTarget,
        setUploadTarget,
        getYearFromValue,
        getElectricityYearWindow,
        validateElectricityYear,
        validateComponentReplLife,
        handleSaveBoundaryRow,
        syncComponentQtyToReplacement,
        onCellChange,
        onRowPatch,
        doDeleteRow,
        renderEditor,
        handleSaveNewRow,
        parseFile,
        validateUpload,
        onUploadSuccess,
        syncComponentUploadToReplacement,
    };
}
